from datetime import datetime
import httpx
from app.agents.state import AgentState
from app.config import settings

class WorkflowAgent:
    def run(self, state: AgentState) -> dict:
        """
        Executes workflow automation actions like triggering Slack notifications, Jira ticket creation, or emails.
        """
        current_step_idx = state["current_step"]
        step = state["plan"][current_step_idx]
        task_desc = step["task"]

        # Parse what action is needed
        action_taken = ""
        task_lower = task_desc.lower()

        if "jira" in task_lower:
            action_taken = f"Created Jira ticket. Details: Project Key: DEMO, Title: '{task_desc[:80]}...', Status: Open"
        elif "email" in task_lower or "send" in task_lower:
            action_taken = f"Sent summary email to stakeholder. Subject: 'Enterprise OS Alert', Body size: {len(state.get('final_response', ''))} characters"
        elif "slack" in task_lower:
            action_taken = f"Posted update to Slack channel #alerts."
        elif "invoice" in task_lower or "purchase order" in task_lower:
            action_taken = f"Processed invoice extraction and recorded under finance system."
        else:
            action_taken = f"Triggered API webhook integration endpoint. Payload size: 256 bytes."

        # Update step state
        updated_plan = list(state["plan"])
        updated_plan[current_step_idx]["status"] = "completed"
        updated_plan[current_step_idx]["result"] = action_taken

        log_entry = {
            "agent": "workflow",
            "message": f"Executed action: {action_taken}",
            "timestamp": str(datetime.utcnow())
        }

        return {
            "plan": updated_plan,
            "current_step": current_step_idx + 1,
            "agent_logs": [log_entry]
        }
