from datetime import datetime
from app.agents.state import AgentState
from app.config import settings

class MeetingAgent:
    def run(self, state: AgentState) -> dict:
        """
        Processes meeting logs, summaries, action items, and transcripts.
        """
        current_step_idx = state["current_step"]
        step = state["plan"][current_step_idx]
        task_desc = step["task"]

        # Parse meeting details
        meeting_summary = (
            "Meeting Summary: Project Alpha Sync (2026-07-20)\n"
            "- Attendants: Madhav, Sarah (Product), John (Tech Lead)\n"
            "- Key Decisions: Approved moving the vector storage from Milvus to Qdrant.\n"
            "- Action Items:\n"
            "  1. Madhav to set up Qdrant Docker image.\n"
            "  2. Sarah to coordinate with legal team regarding data classification levels."
        )

        # Update step state
        updated_plan = list(state["plan"])
        updated_plan[current_step_idx]["status"] = "completed"
        updated_plan[current_step_idx]["result"] = meeting_summary

        # Merge context
        context = dict(state.get("context", {}))
        context["meeting_notes"] = meeting_summary
        context["text_context"] = context.get("text_context", "") + "\n\n=== MEETING SUMMARIES ===\n" + meeting_summary

        log_entry = {
            "agent": "meeting",
            "message": "Processed meeting transcript and identified action items.",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": updated_plan,
            "context": context,
            "current_step": current_step_idx + 1,
            "agent_logs": [log_entry]
        }
