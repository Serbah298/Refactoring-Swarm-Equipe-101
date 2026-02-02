import json
import os
import uuid
from datetime import datetime
from enum import Enum

LOG_FILE = os.path.join("logs", "experiment_data.json")


class ActionType(str, Enum):
    ANALYSIS = "CODE_ANALYSIS"
    GENERATION = "CODE_GEN"
    DEBUG = "DEBUG"
    FIX = "FIX"


ALLOWED_STATUS = {"SUCCESS", "FAILURE"}


def log_experiment(
    agent_name: str,
    model_used: str,
    action: ActionType,
    details: dict,
    status: str
):
    # --- 1. Validation Action ---
    if isinstance(action, ActionType):
        action_str = action.value
    else:
        raise ValueError("Action must be an ActionType enum")

    # --- 2. Validation status ---
    if status not in ALLOWED_STATUS:
        raise ValueError(
            f"Invalid status '{status}'. Allowed: {ALLOWED_STATUS}"
        )

    # --- 3. Validation details ---
    if not isinstance(details, dict):
        raise ValueError("details must be a dictionary")

    required_keys = {"input_prompt", "output_response"}
    missing = required_keys - details.keys()
    if missing:
        raise ValueError(
            f"Missing required detail fields: {missing}"
        )

    # --- 4. Prepare entry ---
    os.makedirs("logs", exist_ok=True)

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "model": model_used,
        "action": action_str,
        "details": details,
        "status": status
    }

    # --- 5. Read existing data ---
    data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except json.JSONDecodeError:
            data = []

    # --- 6. Write ---
    data.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
