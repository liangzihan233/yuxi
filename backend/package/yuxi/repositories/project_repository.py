"""项目数据访问层"""

from typing import Any

from sqlalchemy import func, select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_interview import Project


class ProjectRepository:
    """项目数据访问层"""

    async def get_by_id(self, id: int) -> Project | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Project).where(Project.id == id))
            return result.scalar_one_or_none()

    async def list_by_department(self, department_id: int) -> list[Project]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Project)
                .where(Project.department_id == department_id)
                .order_by(Project.created_at.desc())
            )
            return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> Project:
        async with pg_manager.get_async_session_context() as session:
            project = Project(**data)
            session.add(project)
        return project

    async def update(self, id: int, data: dict[str, Any]) -> Project | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Project).where(Project.id == id))
            project = result.scalar_one_or_none()
            if project is None:
                return None
            for key, value in data.items():
                if key != "id":
                    setattr(project, key, value)
        return project

    async def delete(self, id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Project).where(Project.id == id))
            project = result.scalar_one_or_none()
            if project is None:
                return False
            await session.delete(project)
        return True

    async def count_by_department(self, department_id: int) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count(Project.id)).where(Project.department_id == department_id)
            )
            return result.scalar() or 0

    async def count_by_status(self, department_id: int, status: str) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count(Project.id)).where(
                    Project.department_id == department_id, Project.status == status
                )
            )
            return result.scalar() or 0
