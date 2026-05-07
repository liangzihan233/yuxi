"""访谈流程数据访问层"""

from typing import Any

from sqlalchemy import select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_interview import InterviewFlow


class InterviewFlowRepository:
    """访谈流程数据访问层"""

    async def get_by_id(self, id: int) -> InterviewFlow | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(InterviewFlow).where(InterviewFlow.id == id))
            return result.scalar_one_or_none()

    async def list_by_project(self, project_id: int) -> list[InterviewFlow]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(InterviewFlow)
                .where(InterviewFlow.project_id == project_id)
                .order_by(InterviewFlow.created_at.desc())
            )
            return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> InterviewFlow:
        async with pg_manager.get_async_session_context() as session:
            flow = InterviewFlow(**data)
            session.add(flow)
        return flow

    async def update(self, id: int, data: dict[str, Any]) -> InterviewFlow | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(InterviewFlow).where(InterviewFlow.id == id))
            flow = result.scalar_one_or_none()
            if flow is None:
                return None
            for key, value in data.items():
                if key != "id":
                    setattr(flow, key, value)
        return flow

    async def delete(self, id: int) -> bool:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(InterviewFlow).where(InterviewFlow.id == id))
            flow = result.scalar_one_or_none()
            if flow is None:
                return False
            await session.delete(flow)
        return True
