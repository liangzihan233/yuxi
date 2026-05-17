"""项目管理路由 - 项目 CRUD、文档上传、访谈流程、访谈记录"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Any
import json

from server.utils.auth_middleware import get_required_user
from yuxi.storage.postgres.models_business import User
from yuxi.services.project_service import ProjectService
from yuxi.services.interview_flow_service import InterviewFlowService
from yuxi.services.interview_service import InterviewService
from yuxi.repositories.interview_repository import InterviewRepository

projects_router = APIRouter(prefix="/projects", tags=["projects"])

project_service = ProjectService()
flow_service = InterviewFlowService()
interview_service = InterviewService()
interview_repo = InterviewRepository()


# --- Pydantic Schemas ---


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    status: str = "draft"
    cover_image: str | None = None
    knowledge_base_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    cover_image: str | None = None
    knowledge_base_id: str | None = None
    ai_summary: dict[str, Any] | None = None


class FlowCreate(BaseModel):
    name: str
    flow_data: dict[str, Any] | None = None
    source_type: str = "manual"
    estimated_duration: int | None = None
    flow_type: str = "chat"
    remark: str | None = None


class FlowUpdate(BaseModel):
    name: str | None = None
    flow_data: dict[str, Any] | None = None
    estimated_duration: int | None = None
    status: str | None = None
    flow_type: str | None = None
    remark: str | None = None


class FlowGenerateRequest(BaseModel):
    name: str
    estimated_duration: int = 30
    flow_type: str = "chat"
    remark: str | None = None


class InterviewCreate(BaseModel):
    name: str
    valid_from: str | None = None
    valid_until: str | None = None
    max_participants: int = 10
    linked_flows: list[int]
    moderator_ids: list[str] = []


class InterviewStatusUpdate(BaseModel):
    status: str


# --- 项目 CRUD ---


@projects_router.get("")
async def list_projects(current_user: User = Depends(get_required_user)):
    return await project_service.list_projects(current_user.department_id)


@projects_router.get("/stats")
async def get_project_stats(current_user: User = Depends(get_required_user)):
    return await project_service.get_project_stats(current_user.department_id)


@projects_router.post("")
async def create_project(data: ProjectCreate, current_user: User = Depends(get_required_user)):
    return await project_service.create_project({**data.model_dump(), "department_id": current_user.department_id, "user_id": current_user.id})


@projects_router.get("/{project_id}")
async def get_project(project_id: int, current_user: User = Depends(get_required_user)):
    return await project_service.get_project(project_id)


@projects_router.put("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, current_user: User = Depends(get_required_user)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    return await project_service.update_project(project_id, update_data)


@projects_router.delete("/{project_id}")
async def delete_project(project_id: int, current_user: User = Depends(get_required_user)):
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "删除成功"}


# --- 文档上传 & AI 完善 ---


@projects_router.post("/{project_id}/upload-document")
async def upload_document(project_id: int, file: UploadFile = File(...), current_user: User = Depends(get_required_user)):
    return await project_service.upload_document(project_id, file)


@projects_router.post("/{project_id}/enrich")
async def enrich_project(project_id: int, current_user: User = Depends(get_required_user)):
    return await project_service.enrich_project(project_id)


@projects_router.delete("/{project_id}/document")
async def delete_document(project_id: int, current_user: User = Depends(get_required_user)):
    return await project_service.delete_document(project_id)


# --- 访谈流程 ---


@projects_router.get("/{project_id}/flows")
async def list_flows(project_id: int, current_user: User = Depends(get_required_user)):
    return await flow_service.list_flows(project_id)


@projects_router.post("/{project_id}/flows")
async def create_flow(project_id: int, data: FlowCreate, current_user: User = Depends(get_required_user)):
    return await flow_service.create_flow({**data.model_dump(), "project_id": project_id})


@projects_router.post("/{project_id}/flows/generate")
async def generate_flow_from_document(project_id: int, data: FlowGenerateRequest, current_user: User = Depends(get_required_user)):
    return await flow_service.generate_from_document(project_id, data.model_dump())


@projects_router.get("/{project_id}/flows/{flow_id}")
async def get_flow(flow_id: int, current_user: User = Depends(get_required_user)):
    return await flow_service.get_flow(flow_id)


@projects_router.put("/{project_id}/flows/{flow_id}")
async def update_flow(flow_id: int, data: FlowUpdate, current_user: User = Depends(get_required_user)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    return await flow_service.update_flow(flow_id, update_data)


@projects_router.post("/{project_id}/flows/{flow_id}/confirm")
async def confirm_flow(flow_id: int, current_user: User = Depends(get_required_user)):
    return await flow_service.confirm_flow(flow_id)


@projects_router.delete("/{project_id}/flows/{flow_id}")
async def delete_flow(flow_id: int, current_user: User = Depends(get_required_user)):
    success = await flow_service.delete_flow(flow_id)
    if not success:
        raise HTTPException(status_code=404, detail="访谈流程不存在")
    return {"message": "删除成功"}


# --- 访谈记录 ---


@projects_router.get("/{project_id}/interviews/validate")
async def validate_project_ready(project_id: int, current_user: User = Depends(get_required_user)):
    """校验项目是否满足创建访谈的条件"""
    return await interview_service.validate_project_ready(project_id)


@projects_router.post("/{project_id}/interviews")
async def create_interview(project_id: int, data: InterviewCreate, current_user: User = Depends(get_required_user)):
    return await interview_service.create_interview(project_id, data.model_dump())


@projects_router.get("/{project_id}/interviews")
async def list_interviews(
    project_id: int,
    status: str | None = Query(None, description="筛选状态: pending/in_progress/completed/analyzing/archived"),
    parent_interview_id: int | None = Query(None, description="主访谈ID，仅返回该访谈及其全部会话记录"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=1000, description="每页数量"),
    current_user: User = Depends(get_required_user),
):
    """分页查询访谈记录列表，支持状态筛选"""
    return await interview_service.list_interviews_paginated(
        project_id,
        status=status,
        page=page,
        page_size=page_size,
        parent_interview_id=parent_interview_id,
    )


@projects_router.get("/{project_id}/interviews/stats")
async def get_interview_stats(project_id: int, current_user: User = Depends(get_required_user)):
    """获取项目访谈统计数据"""
    return await interview_service.get_interview_stats(project_id)


@projects_router.get("/{project_id}/interviews/{interview_id}")
async def get_interview(interview_id: int, current_user: User = Depends(get_required_user)):
    interview = await interview_repo.get_by_id(interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="访谈记录不存在")
    return interview.to_dict()


@projects_router.get("/{project_id}/interviews/{interview_id}/export")
async def export_interview_transcript(
    project_id: int,
    interview_id: int,
    current_user: User = Depends(get_required_user),
):
    interview = await interview_repo.get_by_id(interview_id)
    if interview is None or interview.project_id != project_id:
        raise HTTPException(status_code=404, detail="访谈记录不存在")

    transcript_text = ""
    if interview.transcript:
        try:
            transcript_items = json.loads(interview.transcript)
            lines = []
            for item in transcript_items:
                role = item.get("role", "unknown")
                content = item.get("content", "")
                timestamp = item.get("time") or ""
                prefix = f"[{timestamp}] " if timestamp else ""
                lines.append(f"{prefix}{role}: {content}")
            transcript_text = "\n".join(lines)
        except Exception:
            transcript_text = interview.transcript

    if not transcript_text:
        transcript_text = "暂无访谈记录"

    filename = f"interview-{interview_id}-transcript.txt"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(transcript_text, headers=headers)


@projects_router.delete("/{project_id}/interviews/{interview_id}")
async def delete_interview(project_id: int, interview_id: int, current_user: User = Depends(get_required_user)):
    await interview_service.delete_interview(interview_id)
    return {"message": "删除成功"}


@projects_router.put("/{project_id}/interviews/{interview_id}/status")
async def update_interview_status(
    project_id: int, interview_id: int, data: InterviewStatusUpdate, current_user: User = Depends(get_required_user)
):
    """更新访谈状态"""
    return await interview_service.update_interview_status(interview_id, data.status)


@projects_router.post("/{project_id}/interviews/{interview_id}/analyze")
async def analyze_interview(
    project_id: int,
    interview_id: int,
    current_user: User = Depends(get_required_user),
):
    """使用系统默认对话模型分析访谈记录"""
    return await interview_service.analyze_interview(project_id, interview_id)


@projects_router.post("/{project_id}/interviews/{interview_id}/archive")
async def archive_interview(
    project_id: int,
    interview_id: int,
    current_user: User = Depends(get_required_user),
):
    """将已完成访谈记录入库到项目对应知识库"""
    return await interview_service.archive_interview_to_knowledge_base(project_id, interview_id)
