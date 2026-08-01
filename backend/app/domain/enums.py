"""
Enterprise AI Copilot — Domain Enumerations
"""
import enum


class RoleEnum(str, enum.Enum):
    employee = "employee"
    team_lead = "team_lead"
    manager = "manager"
    hr = "hr"
    administrator = "administrator"


class PermissionEnum(str, enum.Enum):
    read = "read"
    write = "write"
    delete = "delete"
    admin = "admin"
    manage_users = "manage_users"
    manage_connectors = "manage_connectors"
    view_analytics = "view_analytics"
    manage_workflows = "manage_workflows"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    archived = "archived"


class DocumentType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    pptx = "pptx"
    xlsx = "xlsx"
    csv = "csv"
    txt = "txt"
    md = "md"
    image = "image"
    email = "email"
    code = "code"
    unknown = "unknown"


class ConnectorType(str, enum.Enum):
    github = "github"
    jira = "jira"
    slack = "slack"
    notion = "notion"
    confluence = "confluence"
    sharepoint = "sharepoint"
    database = "database"
    rest_api = "rest_api"
    cloud_storage = "cloud_storage"
    email = "email"


class ConnectorStatus(str, enum.Enum):
    disconnected = "disconnected"
    connected = "connected"
    syncing = "syncing"
    error = "error"


class SyncFrequency(str, enum.Enum):
    manual = "manual"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    realtime = "realtime"


class AgentType(str, enum.Enum):
    planner = "planner"
    retrieval = "retrieval"
    reasoning = "reasoning"
    report = "report"
    workflow = "workflow"
    code = "code"
    meeting = "meeting"
    analytics = "analytics"


class AgentStatus(str, enum.Enum):
    idle = "idle"
    planning = "planning"
    executing = "executing"
    completed = "completed"
    error = "error"


class WorkflowStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    running = "running"
    completed = "completed"
    failed = "failed"
    paused = "paused"


class AuditAction(str, enum.Enum):
    login = "login"
    logout = "logout"
    create = "create"
    read = "read"
    update = "update"
    delete = "delete"
    upload = "upload"
    download = "download"
    search = "search"
    chat = "chat"
    agent_execution = "agent_execution"
    connector_sync = "connector_sync"
    workflow_run = "workflow_run"
    permission_change = "permission_change"


class SearchMode(str, enum.Enum):
    semantic = "semantic"
    keyword = "keyword"
    hybrid = "hybrid"


class ChunkStrategy(str, enum.Enum):
    recursive = "recursive"
    semantic = "semantic"
    parent_child = "parent_child"
    sentence = "sentence"


# ─── RBAC Role-Permission Mapping ─────────────────────────
ROLE_PERMISSIONS: dict[RoleEnum, set[PermissionEnum]] = {
    RoleEnum.employee: {PermissionEnum.read, PermissionEnum.write},
    RoleEnum.team_lead: {PermissionEnum.read, PermissionEnum.write, PermissionEnum.delete},
    RoleEnum.manager: {
        PermissionEnum.read, PermissionEnum.write, PermissionEnum.delete,
        PermissionEnum.view_analytics,
    },
    RoleEnum.hr: {
        PermissionEnum.read, PermissionEnum.write, PermissionEnum.delete,
        PermissionEnum.manage_users, PermissionEnum.view_analytics,
    },
    RoleEnum.administrator: {
        p for p in PermissionEnum  # all permissions
    },
}
