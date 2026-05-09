"""访谈实例用例层 - 创建访谈链接、删除访谈、项目就绪校验"""

import json
import uuid
from datetime import datetime
import traceback
import os
import tempfile

from fastapi import HTTPException

from yuxi.repositories.interview_flow_repository import InterviewFlowRepository
from yuxi.repositories.interview_repository import InterviewRepository
from yuxi.repositories.project_repository import ProjectRepository
from yuxi.models.chat import select_model
from yuxi import config, knowledge_base
from yuxi.utils.logging_config import logger


def _parse_datetime_str(val: str | None) -> datetime | None:
    """将前端本地日期时间字符串转为本地 naive datetime（与数据库展示保持一致）"""
    if not val:
        return None
    normalized = str(val).strip().replace("T", " ")
    return datetime.fromisoformat(normalized)


class InterviewService:
    """访谈实例用例层"""

    ANALYSIS_PROMPT = """
你是一名资深访谈内容分析助手。请对输入的访谈记录执行以下操作：
1. 剔除明显与访谈主题无关的寒暄、技术噪音、重复口头语、无意义打断、纯流程控制类对话。
2. 保留与真实访谈问题、追问、回答、澄清直接相关的内容。
3. 输出一份整理后的访谈记录，保持原始问答语义，不要编造。
4. 在文档末尾追加一个非常简要且精准的“AI_CALL_SUMMARY”区块，供其他 AI 工具调用。

输出格式必须严格如下：
---CLEAN_TRANSCRIPT---
这里放整理后的访谈记录
---AI_CALL_SUMMARY---
[
  {
    "question": "问题1",
    "answer": "非常简要的精准回答摘要"
  }
]

要求：
- summary 只保留核心问题与核心回答。
- 每条 answer 尽量 1~2 句话，避免冗长。
- 如果某一轮没有有效回答，不要写入 summary。
- 不要输出任何额外解释。
"""

    def __init__(self):
        self.interview_repo = InterviewRepository()
        self.project_repo = ProjectRepository()
        self.flow_repo = InterviewFlowRepository()

    async def validate_project_ready(self, project_id: int) -> dict:
        """校验项目是否满足创建访谈的前提条件，返回校验结果和缺失项"""
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

        missing = []
        if not project.document_url:
            missing.append("文档未上传")
        if not project.ai_summary:
            missing.append("AI 解析未完成")

        confirmed_flows = await self.flow_repo.list_by_project(project_id)
        confirmed_flows = [f for f in confirmed_flows if f.status == "confirmed"]
        if not confirmed_flows:
            missing.append("无已确认的访谈流程")

        return {"ready": len(missing) == 0, "missing": missing, "confirmed_flows": confirmed_flows}

    async def create_interview(self, project_id: int, data: dict) -> dict:
        """创建访谈记录，含前置校验"""
        validation = await self.validate_project_ready(project_id)
        if not validation["ready"]:
            detail = "；".join(validation["missing"])
            raise HTTPException(status_code=400, detail=f"项目尚未就绪：{detail}")

        # 校验 linked_flows 中的 ID 都是该项目的已确认流程
        linked_flow_ids = data.get("linked_flows", [])
        if not linked_flow_ids:
            raise HTTPException(status_code=400, detail="请至少关联一个访谈流程")

        confirmed_ids = {f.id for f in validation["confirmed_flows"]}
        invalid_ids = set(linked_flow_ids) - confirmed_ids
        if invalid_ids:
            raise HTTPException(
                status_code=400, detail=f"关联流程 {invalid_ids} 不存在或未确认"
            )

        interview = await self.interview_repo.create(
            {
                "project_id": project_id,
                "status": "pending",
                "name": data.get("name"),
                "interview_token": str(uuid.uuid4()),
                "valid_from": _parse_datetime_str(data.get("valid_from")),
                "valid_until": _parse_datetime_str(data.get("valid_until")),
                "max_participants": data.get("max_participants", 10),
                "linked_flows": data.get("linked_flows", []),
            }
        )
        return interview.to_dict()

    async def delete_interview(self, interview_id: int) -> bool:
        """删除访谈记录"""
        success = await self.interview_repo.delete(interview_id)
        if not success:
            raise HTTPException(status_code=404, detail="访谈记录不存在")
        return True

    # --- 统计与列表 ---

    VALID_STATUS_TRANSITIONS = {
        "pending": {"in_progress", "completed"},
        "in_progress": {"completed"},
        "completed": {"analyzing"},
        "analyzing": {"archived", "completed"},
        "archived": {"analyzing"},
    }

    async def get_interview_stats(self, project_id: int) -> dict:
        """获取项目访谈统计数据"""
        return await self.interview_repo.get_stats(project_id)

    async def list_interviews_paginated(
        self,
        project_id: int,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
        parent_interview_id: int | None = None,
    ) -> dict:
        """分页查询访谈列表"""
        valid_statuses = {"pending", "in_progress", "completed", "analyzing", "archived"}
        if status and status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")

        result = await self.interview_repo.list_by_project_paginated(
            project_id,
            status=status,
            page=page,
            page_size=page_size,
            parent_interview_id=parent_interview_id,
        )
        serialized_items = [await self._serialize_interview_with_display_status(i) for i in result["items"]]
        if parent_interview_id is not None and status == "completed":
            serialized_items = [item for item in serialized_items if self._has_meaningful_transcript(item.get("transcript"))]
        return {
            "items": serialized_items,
            "total": len(serialized_items) if parent_interview_id is not None and status == "completed" else result["total"],
        }

    async def update_interview_status(self, interview_id: int, new_status: str) -> dict:
        """更新访谈状态，校验流转合法性"""
        valid_statuses = {"pending", "in_progress", "completed", "analyzing", "archived"}
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效的状态值: {new_status}")

        interview = await self.interview_repo.get_by_id(interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="访谈记录不存在")

        current = interview.status
        allowed = self.VALID_STATUS_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"不允许从「{current}」切换到「{new_status}」",
            )

        updated = await self.interview_repo.update(interview_id, {"status": new_status})
        if updated is None:
            raise HTTPException(status_code=404, detail="访谈记录不存在")
        return updated.to_dict()

    async def analyze_interview(self, project_id: int, interview_id: int) -> dict:
        interview = await self.interview_repo.get_by_id(interview_id)
        if interview is None or interview.project_id != project_id:
            raise HTTPException(status_code=404, detail="访谈记录不存在")

        if not interview.transcript:
            raise HTTPException(status_code=400, detail="当前访谈记录暂无可分析内容")

        transcript_text = self._normalize_transcript_for_analysis(interview.transcript)
        if not transcript_text.strip():
            raise HTTPException(status_code=400, detail="当前访谈记录暂无有效文本")

        await self.interview_repo.update(interview_id, {"status": "analyzing"})

        try:
            model = select_model(model_spec=getattr(config, "default_model", ""))
            response = await model.call([
                {"role": "system", "content": self.ANALYSIS_PROMPT},
                {"role": "user", "content": transcript_text},
            ], stream=False)
            analyzed_text = (response.content or "").strip()
            if not analyzed_text:
                raise HTTPException(status_code=500, detail="模型未返回分析结果")

            updated = await self.interview_repo.update(
                interview_id,
                {
                    "summary": self._build_analysis_summary(analyzed_text),
                    "status": "analyzing",
                },
            )
            if updated is None:
                raise HTTPException(status_code=404, detail="访谈记录不存在")
            return updated.to_dict()
        except HTTPException:
            await self.interview_repo.update(interview_id, {"status": "completed"})
            raise
        except Exception as exc:
            logger.error(f"Analyze interview failed: {exc}")
            await self.interview_repo.update(interview_id, {"status": "completed"})
            raise HTTPException(status_code=500, detail=f"分析失败: {exc}")

    def _normalize_transcript_for_analysis(self, transcript: str) -> str:
        try:
            transcript_items = json.loads(transcript)
            if isinstance(transcript_items, list):
                lines = []
                for item in transcript_items:
                    if not isinstance(item, dict):
                        continue
                    role = item.get("role", "unknown")
                    content = str(item.get("content", "")).strip()
                    if not content:
                        continue
                    lines.append(f"{role}: {content}")
                return "\n".join(lines)
        except Exception:
            pass
        return transcript

    def _extract_summary_block(self, analyzed_text: str) -> str:
        marker = "---AI_CALL_SUMMARY---"
        if marker not in analyzed_text:
            return ""
        return analyzed_text.split(marker, 1)[1].strip()

    def _extract_clean_transcript_block(self, analyzed_text: str) -> str:
        start_marker = "---CLEAN_TRANSCRIPT---"
        end_marker = "---AI_CALL_SUMMARY---"
        if start_marker not in analyzed_text:
            return analyzed_text.strip()
        content = analyzed_text.split(start_marker, 1)[1]
        if end_marker in content:
            content = content.split(end_marker, 1)[0]
        return content.strip()

    def _build_analysis_summary(self, analyzed_text: str) -> str:
        clean_transcript = self._extract_clean_transcript_block(analyzed_text)
        ai_call_summary = self._extract_summary_block(analyzed_text)
        sections = []
        if clean_transcript:
            sections.append(f"---CLEAN_TRANSCRIPT---\n{clean_transcript}")
        if ai_call_summary:
            sections.append(f"---AI_CALL_SUMMARY---\n{ai_call_summary}")
        return "\n\n".join(sections).strip()

    def _has_meaningful_transcript(self, transcript: str | None) -> bool:
        if not transcript:
            return False
        text = str(transcript).strip()
        if not text:
            return False
        return text not in {"暂无访谈记录", "[]", "null", "None"}

    async def _serialize_interview_with_display_status(self, interview) -> dict:
        data = interview.to_dict()
        if interview.parent_interview_id is None:
            data["session_count"] = await self.interview_repo.count_sessions_by_parent_interview(interview.id)
        else:
            data["session_count"] = None
        data["status"] = self._resolve_interview_display_status(interview, session_count=data.get("session_count"))
        return data

    def _resolve_interview_display_status(self, interview, session_count: int | None = None) -> str:
        if interview.parent_interview_id is None:
            effective_session_count = session_count if session_count is not None else 0
            if effective_session_count >= max(interview.max_participants or 1, 1):
                return "completed"
            if interview.status == "archived":
                return "archived"
            if interview.status == "analyzing":
                return "analyzing"

        elif interview.status in {"analyzing", "archived"}:
            return interview.status

        now = datetime.now()
        started = interview.valid_from is None or interview.valid_from <= now
        expired = bool(interview.valid_until and interview.valid_until <= now)

        if expired:
            return "completed"
        if not started:
            return "pending"

        if interview.parent_interview_id is None:
            effective_session_count = session_count if session_count is not None else 0
            if effective_session_count >= max(interview.max_participants or 1, 1):
                return "completed"
            if interview.status == "completed":
                return "completed"
            return "in_progress"

        return interview.status or "completed"

    async def archive_interview_to_knowledge_base(self, project_id: int, interview_id: int) -> dict:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

        interview = await self.interview_repo.get_by_id(interview_id)
        if interview is None or interview.project_id != project_id:
            raise HTTPException(status_code=404, detail="访谈记录不存在")

        if interview.archived_db_id and interview.archived_file_id:
            raise HTTPException(status_code=400, detail="该访谈记录已入库，请勿重复操作")

        display_status = self._resolve_interview_display_status(interview)
        if display_status != "completed":
            raise HTTPException(status_code=400, detail="仅已完成的访谈记录可入库")

        archive_documents = await self._build_archive_documents(project.name, interview)
        if not archive_documents:
            if interview.archived_db_id and interview.archived_file_id:
                raise HTTPException(status_code=400, detail="该访谈记录已入库，请勿重复操作")
            raise HTTPException(status_code=400, detail="当前访谈记录暂无可入库内容")

        database_name = project.name
        databases = await knowledge_base.get_databases()
        writable_kb_types = {"milvus", "lightrag"}
        preferred_kb_type = "milvus" if "milvus" in writable_kb_types else "lightrag"
        target_db = None

        if getattr(project, "knowledge_base_id", None):
            bound_db = next(
                (db for db in databases.get("databases", []) if db.get("db_id") == project.knowledge_base_id),
                None,
            )
            if bound_db and (bound_db.get("kb_type") or "").lower() in writable_kb_types:
                target_db = bound_db

        if target_db is None:
            target_db = next(
                (
                    db for db in databases.get("databases", [])
                    if db.get("name") == database_name and (db.get("kb_type") or "").lower() in writable_kb_types
                ),
                None,
            )

        archive_database_name = database_name
        db_id = None
        created_new_db = False
        if target_db is None:
            name_conflict_db = next(
                (db for db in databases.get("databases", []) if db.get("name") == database_name),
                None,
            )
            if name_conflict_db is not None and (name_conflict_db.get("kb_type") or "").lower() not in writable_kb_types:
                archive_database_name = f"{database_name}-访谈知识库"

            try:
                created = await knowledge_base.create_database(
                    archive_database_name,
                    f"项目 {project.name} 的访谈知识库",
                    kb_type=preferred_kb_type,
                    embed_info=None,
                    llm_info=None,
                    auto_generate_questions=False,
                )
                db_id = created.get("db_id")
                created_new_db = bool(db_id)
            except ValueError as exc:
                if "已存在" not in str(exc):
                    raise

            databases = await knowledge_base.get_databases()
            target_db = next(
                (
                    db for db in databases.get("databases", [])
                    if ((db_id and db.get("db_id") == db_id) or db.get("name") == archive_database_name)
                    and (db.get("kb_type") or "").lower() in writable_kb_types
                ),
                None,
            )
            if target_db is not None:
                db_id = target_db["db_id"]
            elif not db_id:
                raise HTTPException(status_code=400, detail=f"访谈入库失败: 知识库 {archive_database_name} 创建后不可用")
        else:
            db_id = target_db["db_id"]

        if not db_id:
            raise HTTPException(status_code=400, detail="访谈入库失败: 未找到可用知识库")

        if getattr(project, "knowledge_base_id", None) != db_id:
            await self.project_repo.update(project_id, {"knowledge_base_id": db_id})

        try:
            indexed_file_ids = []
            archived_children = []
            for document in archive_documents:
                safe_title = await self._build_unique_archive_filename(db_id, document["title"], document.get("interview_id"))
                tmp_dir = tempfile.mkdtemp(prefix="interview_archive_")
                tmp_path = os.path.join(tmp_dir, safe_title)
                with open(tmp_path, "w", encoding="utf-8") as tmp:
                    tmp.write(document["content"])
                try:
                    file_meta = await knowledge_base.add_file_record(
                        db_id,
                        tmp_path,
                        params={"content_type": "file"},
                        operator_id="system",
                    )
                    file_id = file_meta["file_id"]
                    await knowledge_base.parse_file(db_id, file_id, operator_id="system")
                    await knowledge_base.update_file_params(
                        db_id,
                        file_id,
                        {"chunk_size": 1000, "chunk_overlap": 200},
                        operator_id="system",
                    )
                    try:
                        await knowledge_base.index_file(db_id, file_id, operator_id="system")
                    except Exception as index_exc:
                        error_message = str(index_exc)
                        if "LightRAG" not in error_message and "Invalid token" not in error_message:
                            raise
                        logger.warning(
                            f"Archive interview index skipped for file {file_id} in db {db_id}: {error_message}"
                        )
                    indexed_file_ids.append(file_id)
                    archived_children.append((document.get("interview_id"), file_id))
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    try:
                        os.rmdir(tmp_dir)
                    except OSError:
                        pass
        except Exception as exc:
            logger.error(f"Archive interview failed: {exc}\n{traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"访谈入库失败: {exc}")

        updated = await self.interview_repo.update(
            interview_id,
            {
                "status": "archived",
                "archived_db_id": db_id,
                "archived_file_id": indexed_file_ids[0] if indexed_file_ids else None,
            },
        )
        for child_interview_id, child_file_id in archived_children:
            if child_interview_id and child_interview_id != interview_id:
                await self.interview_repo.update(
                    child_interview_id,
                    {
                        "archived_db_id": db_id,
                        "archived_file_id": child_file_id,
                    },
                )
        return {
            "database_id": db_id,
            "file_id": indexed_file_ids[0] if indexed_file_ids else None,
            "file_ids": indexed_file_ids,
            "interview": await self._serialize_interview_with_display_status(updated),
        }

    async def _build_archive_documents(self, project_name: str, interview) -> list[dict[str, str]]:
        if interview.parent_interview_id is not None:
            if interview.archived_db_id and interview.archived_file_id:
                return []
            transcript_text = self._normalize_transcript_for_analysis(interview.transcript or "").strip()
            if not transcript_text:
                return []
            summary = self._normalize_summary_text(interview.summary)
            return [{
                "interview_id": interview.id,
                "title": self._build_archive_title(interview),
                "content": self._build_archive_document(project_name, interview, transcript_text, summary),
            }]

        child_interviews = await self.interview_repo.list_children_by_parent_interview(interview.id)
        documents = []
        for child in child_interviews:
            if child.archived_db_id and child.archived_file_id:
                continue
            transcript_text = self._normalize_transcript_for_analysis(child.transcript or "").strip()
            if not transcript_text:
                continue
            summary = self._normalize_summary_text(child.summary)
            documents.append({
                "interview_id": child.id,
                "title": self._build_archive_title(child),
                "content": self._build_archive_document(project_name, child, transcript_text, summary),
            })

        if documents:
            return documents

        transcript_text = self._normalize_transcript_for_analysis(interview.transcript or "").strip()
        if not transcript_text or (interview.archived_db_id and interview.archived_file_id):
            return []
        summary = self._normalize_summary_text(interview.summary)
        return [{
            "interview_id": interview.id,
            "title": self._build_archive_title(interview),
            "content": self._build_archive_document(project_name, interview, transcript_text, summary),
        }]

    def _normalize_summary_text(self, summary) -> str:
        if not summary:
            return ""
        if isinstance(summary, str):
            return summary.strip()
        try:
            return json.dumps(summary, ensure_ascii=False, indent=2).strip()
        except Exception:
            return str(summary).strip()

    def _build_archive_title(self, interview) -> str:
        interview_name = (getattr(interview, "name", None) or "").strip()
        if interview_name:
            return f"{interview_name}.md"
        return f"访谈记录_{interview.id}.md"

    async def _build_unique_archive_filename(self, db_id: str, filename: str, interview_id: int | None = None) -> str:
        sanitized = self._sanitize_archive_filename(filename)
        if not await knowledge_base.file_name_existed_in_db(db_id, sanitized):
            return sanitized

        if "." in sanitized:
            stem, ext = sanitized.rsplit(".", 1)
            ext = f".{ext}"
        else:
            stem, ext = sanitized, ""

        if interview_id is not None:
            candidate = f"{stem}_{interview_id}{ext}"
            if not await knowledge_base.file_name_existed_in_db(db_id, candidate):
                return candidate

        suffix = 2
        while True:
            candidate = f"{stem}_{suffix}{ext}"
            if not await knowledge_base.file_name_existed_in_db(db_id, candidate):
                return candidate
            suffix += 1

    def _sanitize_archive_filename(self, filename: str) -> str:
        safe = str(filename or "archive.md").strip()
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            safe = safe.replace(char, '_')
        if not safe.endswith('.md'):
            safe = f"{safe}.md"
        return safe or "archive.md"

    def _build_archive_document(self, project_name: str, interview, transcript_text: str, summary: str = "") -> str:
        started_at = interview.started_at.isoformat() if interview.started_at else ""
        completed_at = interview.completed_at.isoformat() if interview.completed_at else ""
        return (
            f"# {project_name} - 访谈记录\n\n"
            f"- 访谈ID: {interview.id}\n"
            f"- 访谈名称: {interview.name or f'访谈 #{interview.id}'}\n"
            f"- 开始时间: {started_at}\n"
            f"- 结束时间: {completed_at}\n\n"
            f"## 访谈内容\n\n{transcript_text}\n\n"
            f"## AI摘要\n\n{summary}\n"
        )
