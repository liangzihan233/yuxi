"""访谈实例用例层 - 创建访谈链接、删除访谈、项目就绪校验"""

from datetime import datetime

from fastapi import HTTPException

from yuxi.repositories.interview_flow_repository import InterviewFlowRepository
from yuxi.repositories.interview_repository import InterviewRepository
from yuxi.repositories.project_repository import ProjectRepository
from yuxi.utils.logging_config import logger


def _parse_datetime_str(val: str | None) -> datetime | None:
    """将日期时间字符串转为 datetime 对象（asyncpg 要求）"""
    if not val:
        return None
    return datetime.fromisoformat(val)


class InterviewService:
    """访谈实例用例层"""

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
