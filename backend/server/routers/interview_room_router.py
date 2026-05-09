"""语音访谈房间路由 - RTC-AIGC 集成接口

提供访谈房间的 RTC 配置获取和结束接口。
受访者通过 interview_token 访问，无需登录认证。
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.utils.auth_middleware import get_current_user
from yuxi.services.interview_room_service import InterviewRoomService
from yuxi.storage.postgres.models_business import User

interview_room_router = APIRouter(prefix="/interviews", tags=["interview-room"])

room_service = InterviewRoomService()


# --- Pydantic Schemas ---


class RtcConfigResponse(BaseModel):
    AppId: str
    RoomId: str
    UserId: str
    Token: str
    WelcomeMessage: str = "您好，欢迎参加这次访谈。"


class StopInterviewRequest(BaseModel):
    transcript: list[dict[str, Any]] | None = None


class StopInterviewResponse(BaseModel):
    id: int
    status: str
    message: str = "访谈已结束"


# --- 路由 ---


@interview_room_router.get("/by-token/{token}")
async def get_interview_by_token(token: str):
    """通过 token 获取访谈基本信息（受访者入口）"""
    interview = await room_service.get_interview_by_token(token)
    if interview is None:
        raise HTTPException(status_code=404, detail="访谈不存在或已过期")
    return interview


@interview_room_router.post("/{interview_id}/rtc-config")
async def get_interview_rtc_config(
    interview_id: int,
    current_user: User | None = Depends(get_current_user),
):
    """获取访谈房间的 RTC 配置，同时启动 AIGC Agent

    受访者通过 interview_token 对应的 interview_id 调用此接口。
    返回 RTC 接入参数（AppId, RoomId, UserId, Token）。
    """
    return await room_service.get_rtc_config(interview_id)


@interview_room_router.post("/{interview_id}/stop")
async def stop_interview_room(
    interview_id: int,
    data: StopInterviewRequest,
    current_user: User | None = Depends(get_current_user),
):
    """结束访谈，停止 AIGC Agent，保存对话记录

    前端在受访者点击"结束访谈"或断开连接时调用。
    """
    result = await room_service.stop_interview(interview_id, transcript=data.transcript)
    return {
        "id": interview_id,
        "status": result.get("status", "completed"),
        "message": "访谈已结束，记录已保存",
    }
