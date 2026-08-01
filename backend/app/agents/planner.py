import json
from datetime import datetime
from langchain_groq import ChatGroq
from app.config import settings
from app.agents.state import AgentState, AgentStep
from langchain_core.messages import SystemMessage, HumanMessage

class PlannerAgent:
    def __init__(self):
        key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else "gsk_dev_fallback_key"
        self.llm = ChatGroq(model_name=settings.LLM_MODEL, groq_api_key=key)

    def run(self, state: AgentState) -> dict:
        """
        Decomposes the task into an executable plan.
        """
        user_query = state["messages"][-1].content
        
        system_prompt = (
            "You are the Lead Planner Agent for an Enterprise AI Operating System.\n"
            "Your task is to decompose complex requests into a list of structured execution steps.\n"
            "Each step must designate one of the following specialized agents:\n"
            "- retrieval: Search enterprise documents, knowledge graph, or database.\n"
            "- reasoning: Synthesize gathered evidence, compare metrics, identify risks, or summarize text.\n"
            "- code: Search code repositories or run python script analysis.\n"
            "- meeting: Process meeting transcripts, minutes, or action items.\n"
            "- workflow: Trigger external automations (send email, create Jira ticket, etc.).\n"
            "- report: Format findings into professional structured reports.\n"
            "- analytics: Analyze audit logs, token counts, or performance metrics.\n\n"
            "Output your response strictly as a JSON list of objects matching this format:\n"
            '[\n'
            '  {"step_id": 1, "agent": "retrieval", "task": "Search for Project Alpha documents and Slack logs", "status": "pending", "result": ""},\n'
            '  {"step_id": 2, "agent": "reasoning", "task": "Identify risks and summarize progress", "status": "pending", "result": ""}\n'
            ']\n'
            "Analyze the user query carefully and return ONLY the JSON list. Do not include markdown code block formatting."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Decompose this task: {user_query}")
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()
        
        # Clean JSON if wrapped in markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            plan = json.loads(content)
            # Validate plan structure
            validated_plan = []
            for idx, item in enumerate(plan):
                validated_plan.append({
                    "step_id": item.get("step_id", idx + 1),
                    "agent": item.get("agent", "retrieval"),
                    "task": item.get("task", ""),
                    "status": "pending",
                    "result": ""
                })
            plan = validated_plan
        except Exception as e:
            # Fallback plan if JSON fails
            plan = [
                {"step_id": 1, "agent": "retrieval", "task": f"Retrieve documents about: {user_query}", "status": "pending", "result": ""},
                {"step_id": 2, "agent": "reasoning", "task": f"Synthesize and answer: {user_query}", "status": "pending", "result": ""}
            ]

        log_entry = {
            "agent": "planner",
            "message": f"Generated plan with {len(plan)} steps.",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": plan,
            "current_step": 0,
            "agent_logs": [log_entry]
        }
