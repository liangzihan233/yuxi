"""访谈实例数据访问层"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, case

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_interview import Interview


class InterviewRepository:
    """访谈实例数据访问层"""

    async def get_by_id(self, id: int) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(Interview).where(Interview.id == id))
            return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Interview).where(Interview.interview_token == token)
            )
            return result.scalar_one_or_none()

    async def get_latest_session_by_parent(self, parent_interview_id: int) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Interview)
                .where(Interview.parent_interview_id == parent_interview_id)
                .order_by(Interview.created_at.desc(), Interview.id.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_by_parent_and_session_uuid(self, parent_interview_id: int, session_uuid: str) -> Interview | None:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Interview).where(
                    Interview.parent_interview_id == parent_interview_id,
                    Interview.session_uuid == session_uuid,
                )
            )
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
            await session.flush()
            await session.refresh(interview)
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

    async def count_sessions_by_parent_interview(self, interview_id: int) -> int:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(func.count(Interview.id)).where(Interview.parent_interview_id == interview_id)
            )
            return result.scalar() or 0

    async def list_children_by_parent_interview(self, parent_interview_id: int) -> list[Interview]:
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(
                select(Interview)
                .where(Interview.parent_interview_id == parent_interview_id)
                .order_by(Interview.completed_at.desc(), Interview.created_at.desc(), Interview.id.desc())
            )
            return list(result.scalars().all())

    async def list_by_project_paginated(
        self,
        project_id: int,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
        parent_interview_id: int | None = None,
    ) -> dict[str, Any]:
        """分页查询访谈列表，支持状态筛选"""
        async with pg_manager.get_async_session_context() as session:
            # 构建基础查询条件
            conditions = [Interview.project_id == project_id]
            if parent_interview_id is not None:
                conditions.append(Interview.parent_interview_id == parent_interview_id)
            else:
                conditions.append(Interview.parent_interview_id.is_(None))
            if status:
                conditions.append(Interview.status == status)

            # 查总数
            count_result = await session.execute(
                select(func.count(Interview.id)).where(*conditions)
            )
            total = count_result.scalar() or 0

            # 查分页数据
            offset = (page - 1) * page_size
            data_result = await session.execute(
                select(Interview)
                .where(*conditions)
                .order_by(Interview.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            items = list(data_result.scalars().all())
            return {"items": items, "total": total}

    async def get_stats(self, project_id: int) -> dict[str, Any]:
        """获取项目访谈统计数据，包含各状态计数和剩余时长"""
        async with pg_manager.get_async_session_context() as session:
            base_condition = Interview.project_id == project_id

            # 各状态计数
            total_result = await session.execute(
                select(func.count(Interview.id)).where(base_condition)
            )
            total = total_result.scalar() or 0

            stats = {"total": total}
            for status in ["pending", "in_progress", "completed", "analyzing", "archived"]:
                result = await session.execute(
                    select(func.count(Interview.id)).where(
                        base_condition, Interview.status == status
                    )
                )
                stats[status] = result.scalar() or 0

            # 计算剩余时长：仅统计 in_progress 且 valid_until 未过期的访谈
            now = datetime.utcnow()
            remaining_result = await session.execute(
                select(Interview.valid_until).where(
                    base_condition,
                    Interview.status == "in_progress",
                    Interview.valid_until > now,
                )
            )
            remaining_seconds = 0
            for row in remaining_result:
                if row[0]:
                    delta = row[0] - now
                    if delta.total_seconds() > 0:
                        remaining_seconds += int(delta.total_seconds())
            stats["remaining_seconds"] = remaining_seconds

            return stats
