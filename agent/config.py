import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "model": "llama-3.1-70b-versatile",
    "max_steps": 30,
    "max_tokens": 100000,
    "risky_tools": ["write_file", "edit_file", "run_command"],
}

def load_config() -> dict:
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **user_config}
    return DEFAULT_CONFIG