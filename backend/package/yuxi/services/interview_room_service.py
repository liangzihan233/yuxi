"""语音访谈房间服务 - RTC-AIGC 集成"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import time
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException

from yuxi.repositories.interview_flow_repository import InterviewFlowRepository
from yuxi.repositories.interview_repository import InterviewRepository
from yuxi.repositories.project_repository import ProjectRepository
from yuxi.utils.logging_config import logger


class InterviewRoomService:
    """语音访谈房间服务

    负责：
    1. 生成 RTC Token
    2. 构建 System Prompt（从 InterviewFlow + Project）
    3. 调用火山引擎 StartVoiceChat/StopVoiceChat OpenAPI
    4. 保存对话记录和生成摘要
    """

    def __init__(self):
        self.interview_repo = InterviewRepository()
        self.project_repo = ProjectRepository()
        self.flow_repo = InterviewFlowRepository()

        # 火山引擎配置（从环境变量读取）
        self.rtc_app_id = os.environ.get("RTC_APP_ID", "")
        self.rtc_app_key = os.environ.get("RTC_APP_KEY", "")
        self.volc_access_key = os.environ.get("VOLC_ACCESS_KEY_ID", "")
        raw_volc_secret_key = os.environ.get("VOLC_SECRET_KEY", "")
        self.volc_secret_key = raw_volc_secret_key.strip()
        self.volc_secret_key_candidates = self._build_volc_secret_key_candidates(raw_volc_secret_key)
        self.ark_endpoint_id = os.environ.get("ARK_ENDPOINT_ID", "")
        self.volc_asr_app_id = os.environ.get("VOLC_ASR_APP_ID", "6065352960")
        self.volc_tts_app_id = os.environ.get("VOLC_TTS_APP_ID", "6065352960")

        # 火山引擎 OpenAPI 常量
        self.volc_api_host = "rtc.volcengineapi.com"
        self.volc_api_version = "2024-12-01"

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def get_interview_by_token(self, token: str) -> dict[str, Any] | None:
        """通过 interview_token 或 interview_id 查找访谈记录"""
        # 优先按 token 查找
        interview = await self.interview_repo.get_by_token(token)
        if interview:
            return interview.to_dict()
        # 回退：尝试将 token 作为整数 id 查找（兼容旧数据）
        try:
            interview_id = int(token)
            interview = await self.interview_repo.get_by_id(interview_id)
            if interview:
                return interview.to_dict()
        except ValueError:
            pass
        return None

    async def get_rtc_config(self, interview_id: int) -> dict[str, Any]:
        """获取访谈房间的 RTC 配置，同时启动 AIGC Agent

        返回：
            {
                "AppId": str,
                "RoomId": str,
                "UserId": str,
                "Token": str,
                "AgentConfig": { ... },
            }
        """
        interview = await self.interview_repo.get_by_id(interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="访谈记录不存在")

        # 校验访谈状态
        if interview.status not in ("pending", "in_progress"):
            raise HTTPException(status_code=400, detail=f"访谈状态为 {interview.status}，无法开始")

        # 校验有效期
        now = datetime.now()
        if interview.valid_from and interview.valid_from > now:
            raise HTTPException(status_code=400, detail="访谈尚未开始")
        if interview.valid_until and interview.valid_until < now:
            raise HTTPException(status_code=400, detail="访谈已过期")

        # 获取项目信息
        project = await self.project_repo.get_by_id(interview.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取关联的访谈流程
        flows = []
        for flow_id in interview.linked_flows or []:
            flow = await self.flow_repo.get_by_id(flow_id)
            if flow:
                flows.append(flow)

        if not flows:
            raise HTTPException(status_code=400, detail="访谈未关联任何流程")

        # 生成 RTC 参数
        room_id = f"interview_{interview_id}"
        user_id = f"user_{interview_id}_{uuid.uuid4().hex[:8]}"
        token = self._generate_rtc_token(room_id, user_id)

        # 构建 System Prompt
        system_prompt = self._build_system_prompt(project, interview, flows)

        # 构建 VoiceChat 配置
        voice_chat_config = self._build_voice_chat_config(
            room_id=room_id,
            user_id=user_id,
            system_prompt=system_prompt,
        )

        # 调用火山引擎 StartVoiceChat
        await self._start_voice_chat(voice_chat_config)

        # 更新访谈状态为进行中
        if interview.status == "pending":
            await self.interview_repo.update(
                interview_id,
                {"status": "in_progress", "started_at": now},
            )

        return {
            "AppId": self.rtc_app_id,
            "RoomId": room_id,
            "UserId": user_id,
            "Token": token,
            "AgentConfig": voice_chat_config.get("AgentConfig", {}),
        }

    async def stop_interview(
        self,
        interview_id: int,
        transcript: list[dict] | None = None,
        session_uuid: str | None = None,
    ) -> dict[str, Any]:
        """结束一次受访会话；达到最大参与人数时结束主访谈"""
        interview = await self.interview_repo.get_by_id(interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="访谈记录不存在")

        parent_interview = interview
        if interview.parent_interview_id:
            parent_interview = await self.interview_repo.get_by_id(interview.parent_interview_id)
            if parent_interview is None:
                raise HTTPException(status_code=404, detail="主访谈记录不存在")

        logger.info(
            "Stopping interview session",
            extra={
                "interview_id": interview_id,
                "parent_interview_id": parent_interview.id,
                "is_child_session": bool(interview.parent_interview_id),
                "transcript_count": len(transcript or []),
            },
        )

        room_id = f"interview_{interview_id}"
        await self._stop_voice_chat(room_id)

        completed_at = datetime.utcnow()
        transcript_text = json.dumps(transcript, ensure_ascii=False) if transcript else None
        has_meaningful_transcript = bool(transcript_text and transcript_text not in {"[]", "null", "None"})
        parent_linked_flows = list(parent_interview.linked_flows or [])
        parent_participant_info = dict(parent_interview.participant_info or {})
        session_started_at = interview.started_at or parent_interview.started_at or completed_at
        session_uuid = session_uuid or f"session_{interview_id}_{int(completed_at.timestamp())}"

        if interview.parent_interview_id is None:
            if not has_meaningful_transcript:
                session_record = None
            else:
                existing_session = await self.interview_repo.get_by_parent_and_session_uuid(parent_interview.id, session_uuid)
                if existing_session is not None:
                    update_data: dict[str, Any] = {
                        "completed_at": completed_at,
                        "started_at": existing_session.started_at or session_started_at,
                    }
                    if transcript_text:
                        update_data["transcript"] = transcript_text
                    session_record = await self.interview_repo.update(existing_session.id, update_data)
                else:
                    latest_session = await self.interview_repo.get_latest_session_by_parent(parent_interview.id)
                    should_reuse_latest = (
                        latest_session is not None
                        and latest_session.status == "completed"
                        and latest_session.completed_at is not None
                        and (completed_at - latest_session.completed_at).total_seconds() <= 30
                        and latest_session.session_uuid is None
                    )

                    if should_reuse_latest:
                        update_data = {
                            "completed_at": completed_at,
                            "started_at": latest_session.started_at or session_started_at,
                            "session_uuid": session_uuid,
                        }
                        if transcript_text:
                            update_data["transcript"] = transcript_text
                        session_record = await self.interview_repo.update(latest_session.id, update_data)
                    else:
                        session_data: dict[str, Any] = {
                            "project_id": parent_interview.project_id,
                            "flow_id": parent_interview.flow_id,
                            "name": parent_interview.name,
                            "interview_token": None,
                            "valid_from": parent_interview.valid_from,
                            "valid_until": parent_interview.valid_until,
                            "max_participants": parent_interview.max_participants,
                            "linked_flows": parent_linked_flows,
                            "parent_interview_id": parent_interview.id,
                            "transcript": transcript_text,
                            "session_uuid": session_uuid,
                            "status": "completed",
                            "participant_info": parent_participant_info,
                            "started_at": session_started_at,
                            "completed_at": completed_at,
                        }
                        logger.info("Creating child interview session record", extra={"session_data": session_data})
                        session_record = await self.interview_repo.create(session_data)
        else:
            update_data = {
                "status": "completed",
                "session_uuid": interview.session_uuid or session_uuid,
                "started_at": interview.started_at or session_started_at,
                "completed_at": completed_at,
            }
            if transcript_text:
                update_data["transcript"] = transcript_text
            session_record = await self.interview_repo.update(interview_id, update_data)

        session_count = await self.interview_repo.count_sessions_by_parent_interview(parent_interview.id)
        max_participants = max(parent_interview.max_participants or 1, 1)
        parent_status = "completed" if session_count >= max_participants else "pending"
        parent_update_data: dict[str, Any] = {
            "status": parent_status,
            "started_at": None if parent_status == "pending" else parent_interview.started_at,
            "completed_at": completed_at if parent_status == "completed" else None,
        }
        await self.interview_repo.update(parent_interview.id, parent_update_data)

        return session_record.to_dict() if session_record else {}

    # ------------------------------------------------------------------
    # System Prompt 构建
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self,
        project,
        interview,
        flows: list,
    ) -> str:
        """将 Project + Interview + InterviewFlow 转换为 AI 访谈 System Prompt

        将访谈记录的基本信息（名称、有效期、人数限制等）和
        访谈流程的详细信息（问题列表、追问策略、流程路径等）
        以结构化参数形式注入 LLMConfig.SystemMessages。
        """
        from datetime import datetime

        # --------------------------------------------------------------
        # 1. 访谈记录基本信息
        # --------------------------------------------------------------
        valid_from = interview.valid_from.strftime("%Y-%m-%d %H:%M") if interview.valid_from else "未设置"
        valid_until = interview.valid_until.strftime("%Y-%m-%d %H:%M") if interview.valid_until else "未设置"

        interview_info = f"""# 访谈基本信息
- 访谈名称：{interview.name or "未命名访谈"}
- 访谈状态：{interview.status}
- 有效时间：{valid_from} 至 {valid_until}
- 最大参与人数：{interview.max_participants} 人
- 关联流程数：{len(flows)} 个
- 关联流程名称：{', '.join(f.name for f in flows) or '未命名流程'}"""

        # --------------------------------------------------------------
        # 2. 项目背景信息（含 AI 摘要和文档摘要）
        # --------------------------------------------------------------
        ai_summary = ""
        if project.ai_summary:
            if isinstance(project.ai_summary, dict):
                summary_items = []
                for k, v in project.ai_summary.items():
                    summary_items.append(f"  - {k}：{v}")
                ai_summary = "\n".join(summary_items)
            else:
                ai_summary = str(project.ai_summary)[:500]

        doc_preview = ""
        if project.document_markdown:
            doc_preview = project.document_markdown[:800] + ("..." if len(project.document_markdown) > 800 else "")

        project_context = f"""# 项目背景
- 项目名称：{project.name}
- 项目描述：{project.description or "暂无描述"}
"""
        if ai_summary:
            project_context += f"""- AI 摘要：
{ai_summary}
"""
        if doc_preview:
            project_context += f"""- 文档预览：
{doc_preview}
"""

        # --------------------------------------------------------------
        # 3. 访谈流程信息（逐个流程详细展开）
        # --------------------------------------------------------------
        flow_details = []
        all_questions = []
        question_index = 0

        for flow in flows:
            flow_type_label = {"chat": "杂谈", "questionnaire": "问卷", "test": "测试"}.get(
                flow.flow_type, flow.flow_type or "未分类"
            )

            flow_info = f"""## 流程：{flow.name}
- 流程类型：{flow_type_label}
- 预计时长：{flow.estimated_duration or '未设置'} 分钟
- 备注：{flow.remark or '无'}
"""
            # 收集该流程的问题
            flow_data = flow.flow_data or {}
            nodes = flow_data.get("nodes", [])
            flow_questions = []

            for node in nodes:
                data = node.get("data", {})
                question = data.get("question") or data.get("label", "")
                if not question:
                    continue
                question_index += 1
                q_info = {
                    "index": question_index,
                    "question": question,
                    "type": data.get("questionType", "open"),
                    "follow_up_max": data.get("followUpMax", data.get("duration", 2)),
                    "strategy": data.get("followUpStrategy", "根据回答内容深入追问"),
                    "duration": data.get("duration", data.get("estimatedMinutes", 3)),
                }
                all_questions.append(q_info)
                flow_questions.append(q_info)

            # 组装该流程的问题列表
            if flow_questions:
                flow_info += "- 问题列表：\n"
                for q in flow_questions:
                    type_label = {"open": "开放题", "choice": "选择题", "rating": "评分题"}.get(q["type"], "开放题")
                    flow_info += f"  {q['index']}. [{type_label}] {q['question']}（追问上限：{q['follow_up_max']}次，预计{q['duration']}分钟）\n"

            flow_details.append(flow_info)

        # 组装完整问题列表（用于行为准则引用）
        questions_text = ""
        for q in all_questions:
            type_label = {"open": "开放题", "choice": "选择题", "rating": "评分题"}.get(q["type"], "开放题")
            questions_text += f"""
{q['index']}. **{q['question']}**
   - 类型：{type_label}
   - 追问上限：{q['follow_up_max']} 次
   - 追问策略：{q['strategy']}
   - 预计时长：{q['duration']} 分钟
"""

        total_duration = sum(q["duration"] for q in all_questions)
        flow_path = " → ".join(str(q["index"]) for q in all_questions)

        # --------------------------------------------------------------
        # 4. 组装最终 System Prompt
        # --------------------------------------------------------------
        prompt = f"""你是一位专业的用户调研访谈主持人。请严格按照以下框架进行对话。

{interview_info}

{project_context}

# 访谈概况
- 总问题数：{len(all_questions)} 题
- 预计总时长：{total_duration} 分钟
- 访谈流程路径：{flow_path}（线性顺序，无分支跳转）

# 你的行为准则
1. 【顺序执行】严格按照问题顺序逐一进行，不得跳跃或遗漏任何问题
2. 【追问控制】每个问题根据回答质量决定是否追问，追问次数不超过该题设定的追问上限
3. 【追问策略】追问应深入挖掘受访者的真实想法，避免简单重复原问题；具体策略参考每题的"追问策略"
4. 【时长把控】注意每题的预计时长，适时引导进入下一题
5. 【语气风格】语气自然亲切，像朋友聊天而非正式问卷，营造轻松的访谈氛围
6. 【话题引导】当受访者离题时，温和地引导回当前问题
7. 【简短回答】如果受访者回答非常简短，用追问鼓励展开，但不过度逼迫
8. 【完成收尾】所有问题完成后，简要总结访谈要点并真诚感谢受访者

# 详细流程信息
{chr(10).join(flow_details)}

# 问题总览
{questions_text}

# 注意事项
- 你是语音访谈主持人，对话通过语音进行，请使用口语化、自然的表达方式
- 每个问题开始时简要说明问题背景，帮助受访者理解
- 认真倾听受访者的回答，根据回答内容灵活调整追问方向
- 尊重受访者，如果对方表示不愿回答某个问题，礼貌跳过并进入下一题"""

        return prompt

    # ------------------------------------------------------------------
    # 配置兼容处理
    # ------------------------------------------------------------------

    def _build_volc_secret_key_candidates(self, secret_key: str) -> list[str]:
        """兼容火山 demo 中使用 base64 编码保存 SecretKey 的配置格式。"""
        secret_key = (secret_key or "").strip()
        if not secret_key:
            return []

        candidates = [secret_key]
        try:
            decoded = base64.b64decode(secret_key, validate=True).decode("utf-8")
            candidates.append(decoded)
        except Exception:
            pass

        encoded = base64.b64encode(secret_key.encode("utf-8")).decode("utf-8")
        candidates.append(encoded)

        return list(dict.fromkeys(candidates))

    # ------------------------------------------------------------------
    # RTC Token 生成
    # ------------------------------------------------------------------

    def _generate_rtc_token(self, room_id: str, user_id: str, expire_seconds: int = 86400) -> str:
        """生成 RTC Token（使用火山引擎算法）

        参考：https://www.volcengine.com/docs/6348/107372
        """
        if not self.rtc_app_id or not self.rtc_app_key:
            # 开发环境返回 mock token
            logger.warning("RTC_APP_ID 或 RTC_APP_KEY 未配置，返回 mock token")
            return "mock_token"

        # 使用 volcengine-python-sdk 的 token 生成
        try:
            from volcengine.rtc.rtc_token import RtcToken

            token = RtcToken(self.rtc_app_id, self.rtc_app_key, room_id, user_id)
            token.add_privilege(RtcToken.PrivPublishStream, 0)
            token.add_privilege(RtcToken.PrivSubscribeStream, 0)
            token.expire_time(int(time.time()) + expire_seconds)
            return token.serialize()
        except Exception as e:
            logger.warning(f"volcengine SDK 生成 RTC Token 失败，使用内置算法: {e}")
            return self._generate_rtc_token_manual(room_id, user_id, expire_seconds)

    def _generate_rtc_token_manual(
        self, room_id: str, user_id: str, expire_seconds: int = 86400
    ) -> str:
        """按火山 RTC AccessToken 二进制格式生成 token，与官方 demo 保持一致。"""
        now = int(time.time())
        expire = now + expire_seconds
        nonce = int.from_bytes(os.urandom(4), "little")

        privileges = {
            0: expire,  # publish stream
            1: expire,  # publish audio stream
            2: expire,  # publish video stream
            3: expire,  # publish data stream
            4: expire,  # subscribe stream
        }

        message = self._pack_rtc_token_message(nonce, now, expire, room_id, user_id, privileges)
        signature = hmac.new(self.rtc_app_key.encode("utf-8"), message, hashlib.sha256).digest()
        content = self._pack_bytes(message) + self._pack_bytes(signature)
        return f"001{self.rtc_app_id}{base64.b64encode(content).decode('utf-8')}"

    def _pack_rtc_token_message(
        self,
        nonce: int,
        issued_at: int,
        expire_at: int,
        room_id: str,
        user_id: str,
        privileges: dict[int, int],
    ) -> bytes:
        chunks = [
            struct.pack("<I", nonce),
            struct.pack("<I", issued_at),
            struct.pack("<I", expire_at),
            self._pack_string(room_id),
            self._pack_string(user_id),
            struct.pack("<H", len(privileges)),
        ]
        for key in sorted(privileges):
            chunks.append(struct.pack("<H", key))
            chunks.append(struct.pack("<I", privileges[key]))
        return b"".join(chunks)

    def _pack_bytes(self, data: bytes) -> bytes:
        return struct.pack("<H", len(data)) + data

    def _pack_string(self, value: str) -> bytes:
        return self._pack_bytes(value.encode("utf-8"))

    # ------------------------------------------------------------------
    # VoiceChat 配置构建
    # ------------------------------------------------------------------

    def _build_voice_chat_config(
        self,
        room_id: str,
        user_id: str,
        system_prompt: str,
    ) -> dict[str, Any]:
        """构建 StartVoiceChat 的请求体"""
        return {
            "AppId": self.rtc_app_id,
            "RoomId": room_id,
            "TaskId": f"task_{room_id}",
            "AgentConfig": {
                "TargetUserId": [user_id],
                "WelcomeMessage": "你好，准备好了我就开始提问咯",
                "UserId": "InterviewBot",
                "EnableConversationStateCallback": True,
            },
            "Config": {
                "ASRConfig": {
                    "Provider": "volcano",
                    "ProviderParams": {
                        "Mode": "smallmodel",
                        "AppId": self.volc_asr_app_id,
                        "Cluster": "volcengine_streaming_common",
                    },
                },
                "TTSConfig": {
                    "Provider": "volcano",
                    "ProviderParams": {
                        "app": {
                            "appid": self.volc_tts_app_id,
                            "cluster": "volcano_tts",
                        },
                        "audio": {
                            "voice_type": "BV001_streaming",
                            "speed_ratio": 1.0,
                            "pitch_ratio": 1.0,
                            "volume_ratio": 1.0,
                        },
                    },
                },
                "LLMConfig": {
                    "Mode": "ArkV3",
                    "EndPointId": self.ark_endpoint_id,
                    "SystemMessages": [system_prompt],
                    "ThinkingType": "disabled",
                },
                "InterruptMode": 0,
            },
        }

    # ------------------------------------------------------------------
    # 火山引擎 OpenAPI 调用
    # ------------------------------------------------------------------

    async def _start_voice_chat(self, voice_chat_config: dict[str, Any]) -> dict[str, Any]:
        """调用火山引擎 StartVoiceChat OpenAPI"""
        return await self._call_volc_api("StartVoiceChat", voice_chat_config)

    async def _stop_voice_chat(self, room_id: str) -> dict[str, Any]:
        """调用火山引擎 StopVoiceChat OpenAPI"""
        payload = {
            "AppId": self.rtc_app_id,
            "RoomId": room_id,
            "TaskId": f"task_{room_id}",
        }
        return await self._call_volc_api("StopVoiceChat", payload)

    async def _call_volc_api(self, action: str, body: dict[str, Any]) -> dict[str, Any]:
        """调用火山引擎 OpenAPI（HMAC-SHA256 签名）"""
        if not self.volc_access_key or not self.volc_secret_key_candidates:
            logger.warning(f"火山引擎 AK/SK 未配置，跳过 {action}")
            return {}

        service = "rtc"
        region = "cn-north-1"
        version = self.volc_api_version
        body_json = json.dumps(body, separators=(",", ":"), ensure_ascii=False)

        # 使用火山引擎官方签名库（SignerV4）
        last_error: Exception | None = None
        for secret_key in self.volc_secret_key_candidates:
            try:
                result = await self._call_volc_api_with_secret(action, body_json, secret_key, region, service, version)
                if secret_key != self.volc_secret_key:
                    self.volc_secret_key = secret_key
                return result
            except HTTPException as e:
                last_error = e
                if e.status_code != 502:
                    raise
                logger.warning(f"火山引擎 API 调用失败，尝试下一个 SecretKey 候选 ({action}): {e.detail}")
            except Exception as e:
                last_error = e
                logger.warning(f"火山引擎 API 调用异常，尝试下一个 SecretKey 候选 ({action}): {e}")

        if isinstance(last_error, HTTPException):
            raise last_error
        raise HTTPException(status_code=502, detail=f"火山引擎 {action} 调用失败")

    async def _call_volc_api_with_secret(
        self,
        action: str,
        body_json: str,
        secret_key: str,
        region: str,
        service: str,
        version: str,
    ) -> dict[str, Any]:
        """使用指定 SecretKey 调用火山引擎 OpenAPI。"""
        try:
            from collections import OrderedDict

            from volcengine.Credentials import Credentials
            from volcengine.auth.SignerV4 import SignerV4
            from volcengine.base.Request import Request

            req = Request()
            req.set_schema("https")
            req.set_method("POST")
            req.set_host(self.volc_api_host)
            req.set_path("/")
            req.set_headers(
                OrderedDict(
                    {
                        "Host": self.volc_api_host,
                        "Content-Type": "application/json",
                    }
                )
            )
            req.set_query(OrderedDict({"Action": action, "Version": version}))
            req.set_body(body_json)

            credentials = Credentials(self.volc_access_key, secret_key, service, region)
            SignerV4.sign(req, credentials)

            url = f"https://{self.volc_api_host}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    params={"Action": action, "Version": version},
                    content=body_json.encode("utf-8"),
                    headers=dict(req.headers),
                )
                response_text = resp.text
                if resp.status_code >= 400:
                    logger.error(
                        f"火山引擎 API HTTP 错误 ({action}): "
                        f"status={resp.status_code}, body={response_text}"
                    )
                    raise HTTPException(status_code=502, detail=f"火山引擎 {action} 调用失败")

                result = resp.json()
                error_info = result.get("ResponseMetadata", {}).get("Error")
                if error_info:
                    logger.error(f"火山引擎 API 业务错误 ({action}): {error_info}")
                    message = error_info.get("Message") or error_info.get("Code") or f"{action} 调用失败"
                    raise HTTPException(status_code=502, detail=f"火山引擎错误：{message}")
                return result
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"火山引擎 API 调用异常 ({action})")
            raise HTTPException(status_code=502, detail=f"火山引擎 {action} 调用异常: {e}") from e
