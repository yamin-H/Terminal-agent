from yamin.setup import load_user_config

DEFAULTS = {
    "model":       "qwen/qwen3.8-27b",
    "max_steps":   30,
    "max_tokens":  100000,
    "risky_tools": ["write_file", "edit_file", "run_command"],
}

def load_config() -> dict:
    return {**DEFAULTS, **load_user_config()}