"""访谈调研领域数据模型 - 项目、访谈流程、访谈实例"""

from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from yuxi.storage.postgres.models_business import Base
from yuxi.utils.datetime_utils import format_utc_datetime, utc_now_naive


class Project(Base):
    """项目模型 - 访谈调研项目的顶层组织单元"""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="项目名称")
    description = Column(Text, nullable=True, comment="项目描述")
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/active/completed/archived")
    cover_image = Column(String(500), nullable=True, comment="封面图 MinIO URL")

    # 文档导入相关
    document_url = Column(String(500), nullable=True, comment="导入文档的 MinIO URL")
    document_markdown = Column(Text, nullable=True, comment="解析后的 Markdown 内容")
    ai_summary = Column(JSON, nullable=True, comment="AI 自动完善的结构化信息")

    # 关联
    knowledge_base_id = Column(String(50), nullable=True, index=True, comment="关联知识库 ID")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True, comment="所属部门")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="创建者")

    # 时间戳
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # 关联关系
    flows = relationship("InterviewFlow", back_populates="project", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "cover_image": self.cover_image,
            "document_url": self.document_url,
            "document_markdown": self.document_markdown,
            "ai_summary": self.ai_summary or {},
            "knowledge_base_id": self.knowledge_base_id,
            "department_id": self.department_id,
            "user_id": self.user_id,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class InterviewFlow(Base):
    """访谈流程模型 - AI 生成的访谈对话树结构"""

    __tablename__ = "interview_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目")
    name = Column(String(200), nullable=False, comment="流程名称")

    # 流程数据（nodes + edges 格式，供前端流程图渲染）
    flow_data = Column(JSON, nullable=False, default=dict, comment="流程结构数据")
    estimated_duration = Column(Integer, nullable=True, comment="预计时长（分钟）")

    # 来源信息
    source_type = Column(String(20), nullable=False, default="document", comment="来源: document/manual")
    source_document_url = Column(String(500), nullable=True, comment="来源文档 URL")

    # 状态
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/confirmed/active")

    # 流程分类
    flow_type = Column(String(20), nullable=True, default="chat", comment="流程类型: chat/questionnaire/test")
    remark = Column(Text, nullable=True, comment="备注")

    # AI 生成时使用的模型
    model_spec = Column(String(100), nullable=True, comment="生成时使用的模型")

    # 时间戳
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # 关联关系
    project = relationship("Project", back_populates="flows")
    interviews = relationship("Interview", back_populates="flow", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "flow_data": self.flow_data or {},
            "estimated_duration": self.estimated_duration,
            "source_type": self.source_type,
            "source_document_url": self.source_document_url,
            "status": self.status,
            "flow_type": self.flow_type,
            "remark": self.remark,
            "model_spec": self.model_spec,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class Interview(Base):
    """访谈实例模型 - 一次具体的访谈记录"""

    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目")
    flow_id = Column(Integer, ForeignKey("interview_flows.id"), nullable=True, index=True, comment="使用的访谈流程")

    # 访谈链接生成相关
    name = Column(String(200), nullable=True, comment="访谈名称")
    valid_from = Column(DateTime, nullable=True, comment="访谈有效开始时间")
    valid_until = Column(DateTime, nullable=True, comment="访谈有效结束时间")
    max_participants = Column(Integer, nullable=False, default=10, comment="最大参与人数")
    linked_flows = Column(JSON, nullable=False, default=list, comment="关联的访谈流程 ID 列表")

    # 关联现有对话体系
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True, comment="关联对话")

    # 访谈内容
    transcript = Column(Text, nullable=True, comment="文字转录内容")
    video_url = Column(String(500), nullable=True, comment="回放视频 MinIO URL")
    audio_url = Column(String(500), nullable=True, comment="音频 MinIO URL")
    summary = Column(Text, nullable=True, comment="AI 生成的访谈摘要")

    # 状态
    status = Column(
        String(20), nullable=False, default="pending", comment="状态: pending/in_progress/completed/analyzing"
    )

    # 参与者信息
    participant_info = Column(JSON, nullable=True, comment="参与者信息")

    # 时间戳
    started_at = Column(DateTime, nullable=True, comment="访谈开始时间")
    completed_at = Column(DateTime, nullable=True, comment="访谈完成时间")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # 关联关系
    project = relationship("Project", back_populates="interviews")
    flow = relationship("InterviewFlow", back_populates="interviews")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "flow_id": self.flow_id,
            "name": self.name,
            "valid_from": format_utc_datetime(self.valid_from),
            "valid_until": format_utc_datetime(self.valid_until),
            "max_participants": self.max_participants,
            "linked_flows": self.linked_flows or [],
            "conversation_id": self.conversation_id,
            "transcript": self.transcript,
            "video_url": self.video_url,
            "audio_url": self.audio_url,
            "summary": self.summary,
            "status": self.status,
            "participant_info": self.participant_info or {},
            "started_at": format_utc_datetime(self.started_at),
            "completed_at": format_utc_datetime(self.completed_at),
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }
