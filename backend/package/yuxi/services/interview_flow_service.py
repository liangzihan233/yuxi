"""访谈流程用例层 - 流程生成、确认、管理"""

import json

from fastapi import HTTPException

from yuxi.models.chat import select_model
from yuxi.plugins.parser import Parser
from yuxi.repositories.interview_flow_repository import InterviewFlowRepository
from yuxi.repositories.project_repository import ProjectRepository
from yuxi.utils.logging_config import logger


class InterviewFlowService:
    """访谈流程用例层"""

    def __init__(self):
        self.repo = InterviewFlowRepository()
        self.project_repo = ProjectRepository()

    async def list_flows(self, project_id: int) -> list[dict]:
        flows = await self.repo.list_by_project(project_id)
        return [f.to_dict() for f in flows]

    async def get_flow(self, flow_id: int) -> dict:
        flow = await self.repo.get_by_id(flow_id)
        if flow is None:
            raise HTTPException(status_code=404, detail="访谈流程不存在")
        return flow.to_dict()

    async def create_flow(self, data: dict) -> dict:
        flow = await self.repo.create(data)
        return flow.to_dict()

    async def update_flow(self, flow_id: int, data: dict) -> dict:
        flow = await self.repo.update(flow_id, data)
        if flow is None:
            raise HTTPException(status_code=404, detail="访谈流程不存在")
        return flow.to_dict()

    async def delete_flow(self, flow_id: int) -> bool:
        return await self.repo.delete(flow_id)

    async def generate_from_document(self, project_id: int, form_data: dict) -> dict:
        """基于项目已上传的文档，AI 生成访谈流程"""
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        if not project.document_markdown:
            raise HTTPException(status_code=400, detail="项目尚未上传文档，无法生成访谈流程")

        # 提取表单数据
        flow_name = form_data.get("name", "访谈流程")
        estimated_duration = form_data.get("estimated_duration", 30)
        flow_type = form_data.get("flow_type", "chat")
        remark = form_data.get("remark", "")

        # 校验流程名称是否重复
        existing_flows = await self.repo.list_by_project(project_id)
        for f in existing_flows:
            if f.name == flow_name:
                raise HTTPException(status_code=400, detail=f"流程名称「{flow_name}」已存在，请使用其他名称")

        # 流程类型映射（用于 Prompt）
        flow_type_label = {"chat": "杂谈", "questionnaire": "问卷", "test": "测试"}.get(flow_type, "杂谈")
        flow_type_instruction = {
            "chat": "这是一个开放式的杂谈访谈，问题设计应偏向开放性、引导性，鼓励受访者自由表达",
            "questionnaire": "这是一个问卷式访谈，问题设计应偏向结构化、选项化，便于统计和量化分析",
            "test": "这是一个测试型访谈，问题设计应包含评估标准和评分维度，便于对受访者进行能力或特征评估",
        }.get(flow_type, "这是一个开放式的杂谈访谈，问题设计应偏向开放性、引导性，鼓励受访者自由表达")

        # 使用系统默认模型生成流程
        prompt = f"""你是一位专业的调研访谈设计专家。请基于以下文档内容和生成条件，设计一个访谈流程。

生成条件：
- 流程名称：{flow_name}
- 流程类型：{flow_type_label}
- 预计总时长：{estimated_duration} 分钟
- 类型说明：{flow_type_instruction}
{"- 备注：" + remark if remark else ""}

要求：
1. 识别文档中所有需要调研的问题/调查项
2. 根据流程类型「{flow_type_label}」调整问题设计风格
3. 为每个问题设计：
   - label: 问题文本
   - questionType: 问题类型（open/choice/rating）
   - followUpMax: 建议追问次数（0-3）
   - followUpStrategy: 追问策略描述
   - estimatedMinutes: 预估访谈时长（分钟）
4. 生成问题间的逻辑顺序
5. 所有问题的 estimatedMinutes 总和应尽量接近 {estimated_duration} 分钟

请以 JSON 格式输出，结构如下：
{{
  "nodes": [
    {{
      "id": "q1",
      "type": "question",
      "data": {{
        "label": "问题文本",
        "questionType": "open",
        "followUpMax": 2,
        "followUpStrategy": "追问策略",
        "estimatedMinutes": 5
      }}
    }}
  ],
  "edges": [
    {{"id": "e1", "source": "q1", "target": "q2"}}
  ]
}}

文档内容：
{project.document_markdown[:8000]}

请直接输出 JSON，不要包含其他内容。"""

        from yuxi.config import config as app_config

        model_spec = app_config.default_model
        model = select_model()
        response = await model.call(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        # 解析 JSON
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            flow_data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"AI 生成的流程 JSON 解析失败: {response_text[:200]}")
            raise HTTPException(status_code=500, detail="AI 生成的流程格式错误，请重试")

        # 计算总预估时长
        estimated_duration = 0
        for node in flow_data.get("nodes", []):
            estimated_duration += node.get("data", {}).get("estimatedMinutes", 5)

        # 创建流程记录
        flow = await self.repo.create(
            {
                "project_id": project_id,
                "name": flow_name,
                "flow_data": flow_data,
                "estimated_duration": estimated_duration,
                "source_type": "document",
                "source_document_url": project.document_url,
                "status": "draft",
                "flow_type": flow_type,
                "remark": remark,
                "model_spec": model_spec,
            }
        )
        return flow.to_dict()

    async def confirm_flow(self, flow_id: int) -> dict:
        """确认访谈流程（draft → confirmed）"""
        flow = await self.repo.get_by_id(flow_id)
        if flow is None:
            raise HTTPException(status_code=404, detail="访谈流程不存在")
        if flow.status != "draft":
            raise HTTPException(status_code=400, detail="只有草稿状态的流程可以确认")
        flow = await self.repo.update(flow_id, {"status": "confirmed"})
        return flow.to_dict()
