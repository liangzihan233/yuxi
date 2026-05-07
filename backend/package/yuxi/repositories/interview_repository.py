"""访谈实例数据访问层"""

from typing import Any

from sqlalchemy import func, select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_interview import Interview


class InterviewRepository:
    """访谈实例数据访问层"""

    async def get_by_id(self, id: int) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Interview).where(Interview.id == id))
            return result.scalar_one_or_none()

    async def list_by_project(self, project_id: int) -> list[Interview]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Interview)
                .where(Interview.project_id == project_id)
                .order_by(Interview.created_at.desc())
            )
            return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> Interview:
        async with pg_manager.get_async_session_context() as session:
            interview = Interview(**data)
            session.add(interview)
        return interview

    async def update(self, id: int, data: dict[str, Any]) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Interview).where(Interview.id == id))
            interview = result.scalar_one_or_none()
            if interview is None:
                return None
            for key, value in data.items():
                if key != "id":
                    setattr(interview, key, value)
        return interview

    async def delete(self, id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Interview).where(Interview.id == id))
            interview = result.scalar_one_or_none()
            if interview is None:
                return False
            await session.delete(interview)
        return True

    async def count_by_project(self, project_id: int) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count(Interview.id)).where(Interview.project_id == project_id)
            )
            return result.scalar() or 0

    async def count_by_project_and_status(self, project_id: int, status: str) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count(Interview.id)).where(
                    Interview.project_id == project_id, Interview.status == status
                )
            )
            return result.scalar() or 0
