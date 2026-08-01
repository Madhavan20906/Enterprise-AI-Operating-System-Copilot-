from datetime import datetime
from langchain_groq import ChatGroq
from app.config import settings
from app.agents.state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage

class ReportAgent:
    def __init__(self):
        key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else "gsk_dev_fallback_key"
        self.llm = ChatGroq(model_name=settings.LLM_MODEL, groq_api_key=key)

    def run(self, state: AgentState) -> dict:
        """
        Formats all compiled evidence, findings, and analysis into a highly structured executive report.
        """
        current_step_idx = state["current_step"]
        step = state["plan"][current_step_idx]
        task_desc = step["task"]
        
        reasoning_output = state["context"].get("reasoning_output", "")
        retrieved_text = state["context"].get("text_context", "")

        system_prompt = (
            "You are the Reporting and Document Design Agent for an Enterprise AI Operating System.\n"
            "Your job is to compile, format, and structure findings into a formal, production-grade markdown report.\n"
            "Include a professional title, executive summary, detailed sections, risks/mitigations (if applicable), and clear citations/sources.\n"
            "Use clear headings, bullet points, and tables to make the report look clean and corporate.\n"
            "Do not fabricate any information. Rely only on the provided reasoning output and retrieved context."
        )

        user_prompt = (
            f"User Task: {task_desc}\n\n"
            f"Reasoning/Synthesis Findings:\n{reasoning_output}\n\n"
            f"Raw Background Context:\n{retrieved_text}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        report_text = response.content.strip()

        # Update step state
        updated_plan = list(state["plan"])
        updated_plan[current_step_idx]["status"] = "completed"
        updated_plan[current_step_idx]["result"] = "Structured report generated."

        log_entry = {
            "agent": "report",
            "message": "Structured markdown executive report generated successfully.",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": updated_plan,
            "final_response": report_text,
            "current_step": current_step_idx + 1,
            "agent_logs": [log_entry]
        }
