import json
import os
from datetime import datetime
from threading import Lock

MEMORY_FILE = "task_memory.json"
_lock = Lock()


def _init_memory():
    if not os.path.exists(MEMORY_FILE):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "meta": {
                        "version": "1.0",
                        "created": datetime.utcnow().isoformat()
                    },
                    "tasks": []
                },
                f,
                indent=2
            )


def _load():
    _init_memory()
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_task(
    user_input: str,
    function_name: str,
    parameters: dict,
    status: str,
    execution_time_ms: int
):
    with _lock:
        data = _load()

        task_id = f"task_{len(data['tasks']) + 1:06d}"

        entry = {
            "id": task_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "function": function_name,
            "parameters": parameters,
            "status": status,
            "execution_time_ms": execution_time_ms
        }

        data["tasks"].append(entry)
        _save(data)


def get_recent_tasks(limit=5):
    data = _load()
    return data["tasks"][-limit:]


def get_tasks_by_function(function_name: str):
    data = _load()
    return [t for t in data["tasks"] if t["function"] == function_name]
