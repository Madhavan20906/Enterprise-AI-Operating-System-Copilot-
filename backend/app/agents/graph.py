from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.planner import PlannerAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.reasoning import ReasoningAgent
from app.agents.report import ReportAgent
from app.agents.workflow import WorkflowAgent
from app.agents.code import CodeAgent
from app.agents.meeting import MeetingAgent
from app.agents.analytics import AnalyticsAgent

# Instantiate agents
planner_agent = PlannerAgent()
retrieval_agent = RetrievalAgent()
reasoning_agent = ReasoningAgent()
report_agent = ReportAgent()
workflow_agent = WorkflowAgent()
code_agent = CodeAgent()
meeting_agent = MeetingAgent()
analytics_agent = AnalyticsAgent()

# Define routing function
def route_next_agent(state: AgentState) -> str:
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    if not plan or current_step >= len(plan):
        return "end"
        
    next_step = plan[current_step]
    agent_name = next_step["agent"]
    
    # Map to graph node names
    if agent_name in ["retrieval", "reasoning", "report", "workflow", "code", "meeting", "analytics"]:
        return agent_name
    return "end"

# Construct State Graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("planner", planner_agent.run)
builder.add_node("retrieval", retrieval_agent.run)
builder.add_node("reasoning", reasoning_agent.run)
builder.add_node("report", report_agent.run)
builder.add_node("workflow", workflow_agent.run)
builder.add_node("code", code_agent.run)
builder.add_node("meeting", meeting_agent.run)
builder.add_node("analytics", analytics_agent.run)

# Add Edges
builder.set_entry_point("planner")

# Route from planner based on plan contents
builder.add_conditional_edges(
    "planner",
    route_next_agent,
    {
        "retrieval": "retrieval",
        "reasoning": "reasoning",
        "report": "report",
        "workflow": "workflow",
        "code": "code",
        "meeting": "meeting",
        "analytics": "analytics",
        "end": END
    }
)

# Every worker agent routes back to check what to do next
for node_name in ["retrieval", "reasoning", "report", "workflow", "code", "meeting", "analytics"]:
    builder.add_conditional_edges(
        node_name,
        route_next_agent,
        {
            "retrieval": "retrieval",
            "reasoning": "reasoning",
            "report": "report",
            "workflow": "workflow",
            "code": "code",
            "meeting": "meeting",
            "analytics": "analytics",
            "end": END
        }
    )

# Compile Graph
agent_graph = builder.compile()
