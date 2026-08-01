from typing import TypedDict, List, Dict, Any, Annotated
from operator import add
from langchain_core.messages import BaseMessage

class AgentStep(TypedDict):
    step_id: int
    agent: str  # planner, retrieval, reasoning, report, workflow, code, meeting, analytics
    task: str
    status: str  # pending, running, completed, failed
    result: str

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add]
    plan: List[AgentStep]
    current_step: int
    context: Dict[str, Any]
    final_response: str
    agent_logs: Annotated[List[Dict[str, Any]], add]
    user_id: int
    org_id: int
    department: str
