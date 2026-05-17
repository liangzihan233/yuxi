"""RoleCard 管理路由"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException

from server.utils.auth_middleware import get_admin_user, get_db
from yuxi.services import rolecard_service as service
from yuxi.storage.postgres.models_business import User
from yuxi.utils import logger

rolecard_router = APIRouter(prefix="/system/roleCard", tags=["roleCard"])


class RoleCardCreateRequest(BaseModel):
    name: str = Field(..., description="唯一标识")
    description: str = Field(..., description="描述")
    system_prompt: str = Field(..., description="系统提示词")


class RoleCardUpdateRequest(BaseModel):
    description: str | None = Field(None, description="描述")
    system_prompt: str | None = Field(None, description="系统提示词")


def _raise_from_value_error(e: ValueError) -> None:
    message = str(e)
    status_code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=status_code, detail=message)


def _raise_internal_error(action: str, error: Exception) -> None:
    logger.exception("RoleCard %s failed: %s", action, error)
    raise HTTPException(status_code=500, detail=f"{action}失败")


def _is_rolecard_name_duplicate_error(error: IntegrityError) -> bool:
    raw_message = str(getattr(error, "orig", error)).lower()
    return (
        "duplicate key" in raw_message
        and "role_cards" in raw_message
        and ("(name)" in raw_message or "role_cards_pkey" in raw_message)
    )


@rolecard_router.get("")
async def list_rolecards_route(
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 RoleCard 列表（管理员可读）"""
    try:
        items = await service.get_all_rolecards(db)
        return {"success": True, "data": items}
    except Exception as e:
        _raise_internal_error("获取列表", e)


@rolecard_router.get("/{name}")
async def get_rolecard_route(
    name: str,
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个 RoleCard（管理员可读）"""
    try:
        item = await service.get_rolecard(name, db)
        if not item:
            raise HTTPException(status_code=404, detail=f"RoleCard '{name}' 不存在")
        return {"success": True, "data": item}
    except HTTPException:
        raise
    except Exception as e:
        _raise_internal_error("获取", e)


@rolecard_router.post("")
async def create_rolecard_route(
    payload: RoleCardCreateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 RoleCard（管理员）"""
    try:
        data = payload.model_dump()
        item = await service.create_rolecard(data, created_by=current_user.username, db=db)
        return {"success": True, "data": item}
    except IntegrityError as e:
        if _is_rolecard_name_duplicate_error(e):
            raise HTTPException(status_code=409, detail=f"RoleCard '{payload.name}' 已存在")
        _raise_internal_error("创建", e)
    except HTTPException:
        raise
    except Exception as e:
        _raise_internal_error("创建", e)


@rolecard_router.put("/{name}")
async def update_rolecard_route(
    name: str,
    payload: RoleCardUpdateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新 RoleCard（管理员）"""
    try:
        data = payload.model_dump(exclude_unset=True)
        item = await service.update_rolecard(name, data, updated_by=current_user.username, db=db)
        if not item:
            raise HTTPException(status_code=404, detail=f"RoleCard '{name}' 不存在")
        return {"success": True, "data": item}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        _raise_internal_error("更新", e)


@rolecard_router.delete("/{name}")
async def delete_rolecard_route(
    name: str,
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 RoleCard（管理员）"""
    try:
        deleted = await service.delete_rolecard(name, db=db)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"RoleCard '{name}' 不存在")
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        _raise_internal_error("删除", e)
