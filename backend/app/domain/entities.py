"""
Enterprise AI Copilot — Domain Entities (SQLAlchemy Models)
Complete enterprise data model: Users, Documents, Conversations, Agents,
Connectors, Workflows, Analytics, Audit Logs, Knowledge Graph Entities.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, Float,
    ForeignKey, DateTime, Enum, JSON, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
from app.domain.enums import (
    RoleEnum, DocumentStatus, DocumentType, ConnectorType,
    ConnectorStatus, SyncFrequency, AgentType, AgentStatus,
    WorkflowStatus, AuditAction, ChunkStrategy,
)


# ═══════════════════════════════════════════════════════════
#  TENANT / ORGANIZATION
# ═══════════════════════════════════════════════════════════

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free")
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    users = relationship("User", back_populates="organization")
    departments = relationship("Department", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    connectors = relationship("DataConnector", back_populates="organization")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="departments")
    parent = relationship("Department", remote_side=[id])
    users = relationship("User", back_populates="department")

    __table_args__ = (
        UniqueConstraint("name", "org_id", name="uq_dept_name_org"),
    )


# ═══════════════════════════════════════════════════════════
#  USERS & AUTH
# ═══════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(512))
    role = Column(Enum(RoleEnum), default=RoleEnum.employee, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    documents = relationship("Document", back_populates="uploader")
    conversations = relationship("Conversation", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")

    __table_args__ = (
        Index("ix_users_org_role", "org_id", "role"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    scopes = Column(JSON, default=list)  # e.g. ["read", "write", "chat"]
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")


# ═══════════════════════════════════════════════════════════
#  DOCUMENTS & INGESTION
# ═══════════════════════════════════════════════════════════

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    doc_type = Column(Enum(DocumentType), default=DocumentType.unknown)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending)

    # Metadata
    title = Column(String(512))
    description = Column(Text)
    language = Column(String(10), default="en")
    page_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    classification = Column(String(100))  # auto-classified category
    tags = Column(JSON, default=list)
    custom_metadata = Column(JSON, default=dict)

    # Chunking & Indexing
    chunk_strategy = Column(Enum(ChunkStrategy), default=ChunkStrategy.recursive)
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100))
    content_hash = Column(String(64), index=True)  # SHA-256 for dedup
    version = Column(Integer, default=1)

    # Ownership & Access
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    org_id = Column(Integer, ForeignKey("organizations.id"))
    department = Column(String(100), index=True)
    access_level = Column(String(50), default="department")  # public, department, private

    # Source tracking
    source_connector_id = Column(Integer, ForeignKey("data_connectors.id"), nullable=True)
    source_url = Column(String(1024))
    external_id = Column(String(255))  # ID from external system

    # Timestamps
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # relationships
    uploader = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    source_connector = relationship("DataConnector")

    __table_args__ = (
        Index("ix_docs_org_status", "org_id", "status"),
        Index("ix_docs_org_dept", "org_id", "department"),
        Index("ix_docs_content_hash", "content_hash"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64))
    token_count = Column(Integer, default=0)

    # Parent-child chunking
    parent_chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    chunk_level = Column(Integer, default=0)  # 0=leaf, 1=parent, 2=grandparent

    # Metadata
    page_number = Column(Integer)
    section_title = Column(String(255))
    chunk_type = Column(String(50), default="text")  # text, table, image_description, code
    extra_metadata = Column(JSON, default=dict)

    # Vector reference
    qdrant_point_id = Column(String(64))

    # relationships
    document = relationship("Document", back_populates="chunks")
    parent_chunk = relationship("DocumentChunk", remote_side=[id])

    __table_args__ = (
        Index("ix_chunks_doc_idx", "document_id", "chunk_index"),
    )


# ═══════════════════════════════════════════════════════════
#  CONVERSATIONS & CHAT
# ═══════════════════════════════════════════════════════════

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="New Conversation")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Context
    system_prompt = Column(Text, nullable=True)
    model = Column(String(100), default="llama-3.3-70b-versatile")
    temperature = Column(Float, default=0.1)
    context_window = Column(Integer, default=8192)

    # Memory
    summary = Column(Text, nullable=True)  # rolling summary for long conversations
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Stats
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")

    __table_args__ = (
        Index("ix_conv_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)

    # Agent metadata
    agent_type = Column(Enum(AgentType), nullable=True)
    tool_calls = Column(JSON, nullable=True)  # tools invoked
    tool_results = Column(JSON, nullable=True)

    # Sources & Citations
    sources = Column(JSON, default=list)  # [{doc_id, chunk_id, filename, score}]
    confidence_score = Column(Float, nullable=True)

    # Token tracking
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    model_used = Column(String(100))
    latency_ms = Column(Integer, default=0)

    # Feedback
    rating = Column(Integer, nullable=True)  # 1-5
    feedback = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    conversation = relationship("Conversation", back_populates="messages")


# ═══════════════════════════════════════════════════════════
#  AGENT EXECUTIONS
# ═══════════════════════════════════════════════════════════

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Agent info
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.idle)
    task_description = Column(Text)

    # Execution plan (for planner agent)
    plan = Column(JSON, nullable=True)  # [{step, agent, task, status}]
    current_step = Column(Integer, default=0)

    # Results
    result = Column(Text, nullable=True)
    result_metadata = Column(JSON, default=dict)
    tools_used = Column(JSON, default=list)
    sources_consulted = Column(JSON, default=list)

    # Performance
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_agent_exec_user_type", "user_id", "agent_type"),
    )


# ═══════════════════════════════════════════════════════════
#  DATA CONNECTORS
# ═══════════════════════════════════════════════════════════

class DataConnector(Base):
    __tablename__ = "data_connectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    connector_type = Column(Enum(ConnectorType), nullable=False)
    status = Column(Enum(ConnectorStatus), default=ConnectorStatus.disconnected)

    # Configuration (encrypted at rest)
    config = Column(JSON, default=dict)  # connection params
    credentials_encrypted = Column(Text, nullable=True)

    # Sync settings
    sync_frequency = Column(Enum(SyncFrequency), default=SyncFrequency.manual)
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    documents_synced = Column(Integer, default=0)
    sync_cursor = Column(String(512), nullable=True)  # pagination cursor

    # Ownership
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Error tracking
    error_message = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="connectors")

    __table_args__ = (
        UniqueConstraint("name", "org_id", name="uq_connector_name_org"),
    )


class ConnectorSyncLog(Base):
    __tablename__ = "connector_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("data_connectors.id"), nullable=False)
    status = Column(String(20), nullable=False)  # started, completed, failed
    documents_added = Column(Integer, default=0)
    documents_updated = Column(Integer, default=0)
    documents_deleted = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)


# ═══════════════════════════════════════════════════════════
#  WORKFLOWS
# ═══════════════════════════════════════════════════════════

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.draft)

    # Definition
    trigger = Column(String(100))  # manual, schedule, event
    schedule_cron = Column(String(100), nullable=True)
    steps = Column(JSON, nullable=False)  # [{type, config, agent_type}]

    # Ownership
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Stats
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    avg_duration_seconds = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    status = Column(String(20), default="running")
    triggered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Execution
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    step_results = Column(JSON, default=list)
    current_step = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)


# ═══════════════════════════════════════════════════════════
#  KNOWLEDGE GRAPH
# ═══════════════════════════════════════════════════════════

class KnowledgeEntity(Base):
    """Tracks entities extracted from documents for the knowledge graph."""
    __tablename__ = "knowledge_entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # person, project, product, etc.
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), index=True)
    description = Column(Text)
    properties = Column(JSON, default=dict)
    neo4j_node_id = Column(String(64), nullable=True)

    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    confidence = Column(Float, default=1.0)
    mention_count = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_kg_entity_org_type", "org_id", "entity_type"),
        UniqueConstraint("normalized_name", "entity_type", "org_id", name="uq_entity_name_type_org"),
    )


class KnowledgeRelation(Base):
    """Tracks relationships between entities."""
    __tablename__ = "knowledge_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(Integer, ForeignKey("knowledge_entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("knowledge_entities.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)  # works_on, manages, mentions, etc.
    properties = Column(JSON, default=dict)
    confidence = Column(Float, default=1.0)
    neo4j_rel_id = Column(String(64), nullable=True)

    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    source_entity = relationship("KnowledgeEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("KnowledgeEntity", foreign_keys=[target_entity_id])


# ═══════════════════════════════════════════════════════════
#  ANALYTICS & AUDIT
# ═══════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(50), nullable=False)  # user, document, conversation, etc.
    resource_id = Column(String(50), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_audit_org_action", "org_id", "action"),
        Index("ix_audit_user_time", "user_id", "created_at"),
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(BigInteger, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)  # query, upload, agent_run, etc.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_metadata = Column(JSON, default=dict)

    # Metrics
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_analytics_org_type_time", "org_id", "event_type", "created_at"),
    )


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(BigInteger, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
