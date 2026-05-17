"""RoleCard 数据访问层"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.models_business import RoleCard
from yuxi.utils.datetime_utils import utc_now_naive


class RoleCardRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def list_all(self) -> list[RoleCard]:
        result = await self.db.execute(select(RoleCard).order_by(RoleCard.updated_at.desc()))
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> RoleCard | None:
        result = await self.db.execute(select(RoleCard).where(RoleCard.name == name))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str,
        tools: list[str] | None,
        model: str | None,
        is_builtin: bool,
        created_by: str | None,
    ) -> RoleCard:
        now = utc_now_naive()
        item = RoleCard(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            model=model,
            enabled=True,
            is_builtin=is_builtin,
            created_by=created_by,
            updated_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update(
        self,
        item: RoleCard,
        *,
        description: str | None,
        system_prompt: str | None,
        updated_by: str | None,
    ) -> RoleCard:
        if description is not None:
            item.description = description
        if system_prompt is not None:
            item.system_prompt = system_prompt
        item.updated_by = updated_by
        item.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: RoleCard) -> None:
        await self.db.delete(item)
        await self.db.commit()
