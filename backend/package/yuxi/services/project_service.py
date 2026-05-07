"""项目用例层 - 项目 CRUD、文档导入、AI 自动完善"""

import json
import os
import tempfile

from fastapi import HTTPException, UploadFile

from yuxi.models.chat import select_model
from yuxi.plugins.parser import Parser, is_supported_file_extension
from yuxi.repositories.interview_repository import InterviewRepository
from yuxi.repositories.project_repository import ProjectRepository
from yuxi.storage.minio.client import MinIOClient, aupload_file_to_minio
from yuxi.utils.logging_config import logger


class ProjectService:
    """项目用例层"""

    def __init__(self):
        self.repo = ProjectRepository()
        self.interview_repo = InterviewRepository()

    async def list_projects(self, department_id: int) -> list[dict]:
        projects = await self.repo.list_by_department(department_id)
        result = []
        for p in projects:
            data = p.to_dict()
            data["interview_count"] = await self.interview_repo.count_by_project(p.id)
            data["completed_count"] = await self.interview_repo.count_by_project_and_status(p.id, "completed")
            data["in_progress_count"] = await self.interview_repo.count_by_project_and_status(p.id, "in_progress")
            result.append(data)
        return result

    async def get_project(self, project_id: int) -> dict:
        project = await self.repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        data = project.to_dict()
        data["interview_count"] = await self.interview_repo.count_by_project(project_id)
        data["completed_count"] = await self.interview_repo.count_by_project_and_status(project_id, "completed")
        data["in_progress_count"] = await self.interview_repo.count_by_project_and_status(project_id, "in_progress")
        return data

    async def create_project(self, data: dict) -> dict:
        project = await self.repo.create(data)
        return project.to_dict()

    async def update_project(self, project_id: int, data: dict) -> dict:
        project = await self.repo.update(project_id, data)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        return project.to_dict()

    async def delete_project(self, project_id: int) -> bool:
        return await self.repo.delete(project_id)

    async def get_project_stats(self, department_id: int) -> dict:
        """获取项目统计概览"""
        total = await self.repo.count_by_department(department_id)
        active = await self.repo.count_by_status(department_id, "active")
        completed = await self.repo.count_by_status(department_id, "completed")
        draft = await self.repo.count_by_status(department_id, "draft")
        return {
            "total": total,
            "active": active,
            "completed": completed,
            "draft": draft,
        }

    async def upload_document(self, project_id: int, file: UploadFile) -> dict:
        """上传文档到项目，上传至 MinIO 并解析为 Markdown"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        if not is_supported_file_extension(file.filename):
            ext = os.path.splitext(file.filename)[1].lower()
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}，支持的格式: PDF、Word(.docx)、Excel(.xlsx/.xls)、TXT、Markdown、PPT、HTML、CSV、JSON、图片",
            )

        file_bytes = await file.read()
        basename, ext = os.path.splitext(file.filename)

        # 上传到 MinIO
        import time

        timestamp = int(time.time() * 1000)
        minio_filename = f"{basename}_{timestamp}{ext}".lower()
        bucket_name = MinIOClient.KB_BUCKETS["documents"]
        object_name = f"projects/{project_id}/upload/{minio_filename}"
        minio_url = await aupload_file_to_minio(bucket_name, object_name, file_bytes)

        # 保存到临时文件后用 Parser 解析
        markdown = ""
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            markdown = await Parser.aparse(source=tmp_path)
        except Exception as e:
            logger.warning(f"文档解析失败: {e}")
            markdown = f"[文档解析失败: {e}]"
        finally:
            os.unlink(tmp_path)

        # 更新项目文档信息
        project = await self.repo.update(
            project_id,
            {"document_markdown": markdown, "document_url": minio_url},
        )
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

        return {"filename": file.filename, "minio_url": minio_url, "markdown": markdown}

    async def enrich_project(self, project_id: int) -> dict:
        """AI 自动完善项目信息（基于已上传的文档内容）"""
        project = await self.repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        if not project.document_markdown:
            raise HTTPException(status_code=400, detail="项目尚未上传文档，无法 AI 完善")

        prompt = f"""基于以下文档内容，提取并生成调研项目的结构化信息。
请以 JSON 格式输出，包含以下字段：
- name: 项目名称（简短概括）
- description: 项目描述（200字以内）
- research_objectives: 研究目标列表
- target_audience: 目标人群
- key_topics: 关键主题列表

文档内容：
{project.document_markdown[:8000]}

请直接输出 JSON，不要包含其他内容。"""

        model = select_model()
        response = await model.call(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            ai_summary = json.loads(text)
        except json.JSONDecodeError:
            ai_summary = {"raw_response": response_text}
            logger.warning(f"AI 返回的 JSON 解析失败，原始响应已保存: {response_text[:200]}")

        updated = await self.repo.update(project_id, {"ai_summary": ai_summary})
        return updated.to_dict() if updated else ai_summary

    async def delete_document(self, project_id: int) -> dict:
        """删除项目已上传的文档"""
        project = await self.repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        if not project.document_url:
            raise HTTPException(status_code=400, detail="项目没有已上传的文档")

        updated = await self.repo.update(project_id, {
            "document_url": None,
            "document_markdown": None,
            "ai_summary": None,
        })
        return {"message": "文档已删除"}
