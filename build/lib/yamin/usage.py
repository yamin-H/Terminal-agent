# Groq qwen3-32b pricing per 1M tokens
PRICING = {
    "qwen/qwen3-32b": {"input": 0.29, "output": 1.16},
}

_session_usage = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}

def track(model: str, input_tokens: int, output_tokens: int):
    price = PRICING.get(model, {"input": 0, "output": 0})
    cost = (input_tokens / 1_000_000 * price["input"]) + (output_tokens / 1_000_000 * price["output"])

    _session_usage["input_tokens"] += input_tokens
    _session_usage["output_tokens"] += output_tokens
    _session_usage["cost"] += cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost
    }

def session_totals():
    return _session_usage.copy()