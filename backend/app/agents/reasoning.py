from datetime import datetime
from langchain_groq import ChatGroq
from app.config import settings
from app.agents.state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage

class ReasoningAgent:
    def __init__(self):
        key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else "gsk_dev_fallback_key"
        self.llm = ChatGroq(model_name=settings.LLM_MODEL, groq_api_key=key)

    def run(self, state: AgentState) -> dict:
        """
        Synthesizes information gathered from various documents and sources.
        """
        current_step_idx = state["current_step"]
        step = state["plan"][current_step_idx]
        task_desc = step["task"]
        
        retrieved_text = state["context"].get("text_context", "")

        system_prompt = (
            "You are the Reasoning and Synthesis Agent for an Enterprise AI Operating System.\n"
            "Your job is to deeply analyze, synthesize, compare, and reason over the provided background context to complete the user's task.\n"
            "Background context is composed of Hybrid Vector Search results and Knowledge Graph connections.\n"
            "If the information is conflicting, outline the contradictions. If there are gaps in information, note them.\n"
            "Provide a logical, well-reasoned answer based ONLY on the evidence provided."
        )

        user_prompt = f"Task: {task_desc}\n\nBackground Context:\n{retrieved_text}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        result_text = response.content.strip()

        # Update step state
        updated_plan = list(state["plan"])
        updated_plan[current_step_idx]["status"] = "completed"
        updated_plan[current_step_idx]["result"] = result_text

        # Add to reasoning output
        context = dict(state.get("context", {}))
        context["reasoning_output"] = context.get("reasoning_output", "") + "\n\n" + result_text

        log_entry = {
            "agent": "reasoning",
            "message": "Successfully synthesized retrieved data and generated logical reasoning.",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": updated_plan,
            "context": context,
            "current_step": current_step_idx + 1,
            "agent_logs": [log_entry]
        }
