"""RoleCard 服务层"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.repositories.rolecard_repository import RoleCardRepository
from yuxi.services.subagent_service import _get_session


async def get_all_rolecards(db: AsyncSession | None = None) -> list[dict[str, Any]]:
    """获取所有 RoleCard（独立存储）"""
    async with _get_session(db) as session:
        repo = RoleCardRepository(session)
        items = await repo.list_all()
    return [item.to_dict() for item in items]


async def get_rolecard(name: str, db: AsyncSession | None = None) -> dict[str, Any] | None:
    """获取单个 RoleCard"""
    async with _get_session(db) as session:
        repo = RoleCardRepository(session)
        item = await repo.get_by_name(name)
    return item.to_dict() if item else None


async def create_rolecard(
    data: dict[str, Any],
    created_by: str | None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """创建 RoleCard（复用相同结构，独立存储）"""
    async with _get_session(db) as session:
        repo = RoleCardRepository(session)
        item = await repo.create(
            name=data["name"],
            description=data["description"],
            system_prompt=data["system_prompt"],
            tools=[],
            model=None,
            is_builtin=False,
            created_by=created_by,
        )
    return item.to_dict()


async def update_rolecard(
    name: str,
    data: dict[str, Any],
    updated_by: str | None,
    db: AsyncSession | None = None,
) -> dict[str, Any] | None:
    """更新 RoleCard"""
    async with _get_session(db) as session:
        repo = RoleCardRepository(session)
        item = await repo.get_by_name(name)
        if not item:
            return None
        if item.is_builtin:
            raise ValueError("内置 RoleCard 不可编辑")
        item = await repo.update(
            item,
            description=data.get("description"),
            system_prompt=data.get("system_prompt"),
            updated_by=updated_by,
        )
    return item.to_dict()


async def delete_rolecard(name: str, db: AsyncSession | None = None) -> bool:
    """删除 RoleCard"""
    async with _get_session(db) as session:
        repo = RoleCardRepository(session)
        item = await repo.get_by_name(name)
        if not item:
            return False
        if item.is_builtin:
            raise ValueError("内置 RoleCard 不可删除")
        await repo.delete(item)
    return True
