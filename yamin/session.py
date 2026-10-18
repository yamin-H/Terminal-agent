import json
from pathlib import Path

SESSION_FILE = ".agent_session.json"

def save_session(messages: list):
    try:
        serializable = []
        for m in messages:
            if isinstance(m, dict):
                serializable.append(m)
        Path(SESSION_FILE).write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not save session: {e}")

def load_session() -> list:
    try:
        if Path(SESSION_FILE).exists():
            return json.loads(Path(SESSION_FILE).read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def clear_session():
    try:
        Path(SESSION_FILE).unlink(missing_ok=True)
    except Exception:
        pass