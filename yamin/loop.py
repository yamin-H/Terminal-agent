import json
import os
import time
from openai import OpenAI
from yamin.tools import TOOL_DEFINITIONS, execute_tool
from yamin.config import load_config
from yamin.setup import load_user_config

config = load_config()

MAX_STEPS   = config["max_steps"]
RISKY_TOOLS = set(config["risky_tools"])

_client = None


def get_client():
    global _client
    if _client is None:
        key = load_user_config().get("groq_api_key") or os.getenv("GROQ_API_KEY")
        _client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
    return _client


def count_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        if isinstance(m, dict):
            content = m.get("content") or ""
            total += len(str(content)) // 4
    return total


def trim_messages(messages: list, max_tokens: int = 100000) -> list:
    if count_tokens(messages) <= max_tokens:
        return messages
    head = messages[:2]
    tail = messages[-10:]
    return head + [{"role": "user", "content": "[Earlier messages trimmed to save context]"}] + tail


def run_loop(task: str, system_prompt: str, messages: list = None):
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": task})
    steps = 0

    while steps < MAX_STEPS:
        yield {"type": "thinking"}

        try:
            trimmed = trim_messages(messages, max_tokens=config["max_tokens"])
            delay   = 5
            stream  = None

            for attempt in range(4):
                try:
                    stream = get_client().chat.completions.create(
                        model=config["model"],
                        messages=[{"role": "system", "content": system_prompt}] + trimmed,
                        tools=TOOL_DEFINITIONS,
                        stream=True,
                    )
                    break
                except Exception as e:
                    err = str(e)
                    is_rate_limit = (
                        "429" in err
                        or "rate limit" in err.lower()
                        or "too many requests" in err.lower()
                    )
                    if is_rate_limit and attempt < 3:
                        yield {"type": "retry", "attempt": attempt + 1, "wait": delay}
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise

            full_content   = ""
            tool_calls_acc = {}

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    full_content += delta.content
                    yield {"type": "stream_token", "token": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        i = tc.index
                        if i not in tool_calls_acc:
                            tool_calls_acc[i] = {"id": tc.id, "name": "", "args": ""}
                        if tc.id:
                            tool_calls_acc[i]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_acc[i]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_acc[i]["args"] += tc.function.arguments

        except KeyboardInterrupt:
            yield {"type": "error", "content": "Interrupted by user."}
            return
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            return

        steps += 1
        tool_calls = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]

        if not tool_calls:
            messages.append({"role": "assistant", "content": full_content})
            yield {"type": "done", "content": full_content or "✓ Done"}
            return

        messages.append({
            "role": "assistant",
            "content": full_content,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["args"]},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            name = tc["name"]
            try:
                args = json.loads(tc["args"] or "{}")
            except ValueError:
                args = {}
            needs_approval = name in RISKY_TOOLS

            approval = yield {
                "type":           "tool_call",
                "name":           name,
                "args":           args,
                "needs_approval": needs_approval,
                "step":           steps,
                "max_steps":      MAX_STEPS,
            }

            if approval == "denied":
                result = "User denied this action."
            else:
                result = execute_tool(name, args)

            yield {"type": "tool_result", "name": name, "result": result, "args": args}

            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result,
            })

    yield {"type": "max_steps"}