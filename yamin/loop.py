import json
import os
import time
import uuid
from openai import OpenAI
from yamin.tools import TOOL_DEFINITIONS, execute_tool
from yamin.config import load_config
from yamin.usage import track

config = load_config()

MAX_STEPS        = config["max_steps"]
RISKY_TOOLS      = set(config["risky_tools"])
MAX_RESULT_CHARS = 4000
RETRY_CODES      = {429, 500, 502, 503, 504, 529}

_client   = None
_tools_ok = True


def get_client():
    global _client
    if _client is None:
        key      = config.get("api_key") or config.get("groq_api_key") or os.getenv("GROQ_API_KEY") or "none"
        base_url = config.get("base_url") or "https://api.groq.com/openai/v1"
        _client  = OpenAI(api_key=key, base_url=base_url)
    return _client


def count_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        if isinstance(m, dict):
            total += len(str(m.get("content") or "")) // 4
            total += len(str(m.get("tool_calls") or "")) // 4
    return total


def trim_messages(messages: list, max_tokens: int = 4000) -> list:
    if count_tokens(messages) <= max_tokens:
        return messages
    head = messages[:2]
    rest = messages[2:]
    while len(rest) > 1 and count_tokens(head + rest) > max_tokens:
        rest.pop(0)
        # never leave a tool result without the assistant message that called it
        while len(rest) > 1 and rest[0].get("role") == "tool":
            rest.pop(0)
    return head + rest


def cap_result(result: str) -> str:
    if len(result) <= MAX_RESULT_CHARS:
        return result
    cut = len(result) - MAX_RESULT_CHARS
    return (
        result[:MAX_RESULT_CHARS]
        + f"\n... [truncated {cut} chars, read a smaller section if you need more]"
    )


def classify_error(e) -> str:
    code = getattr(e, "status_code", None)
    text = str(e).lower()
    if code in RETRY_CODES or "overloaded" in text or "too many requests" in text:
        return "retry"
    if "tool" in text and ("not support" in text or "unsupported" in text):
        return "no_tools"
    return "fatal"


def friendly_error(e) -> str:
    code  = getattr(e, "status_code", None)
    hints = {
        401: "Invalid API key. Run `yamin --setup` to change it.",
        402: "No credits left on this provider account.",
        404: "Model or endpoint not found. Run `yamin --setup` to pick another model.",
        413: "Request too large for this model or plan. Try /clear or a smaller task.",
    }
    raw = str(e)[:400]
    return f"{hints[code]}\n  {raw}" if code in hints else raw


def run_loop(task: str, system_prompt: str, messages: list = None):
    global _tools_ok

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
                    kwargs = {"tools": TOOL_DEFINITIONS} if _tools_ok else {}
                    stream = get_client().chat.completions.create(
                        model=config["model"],
                        messages=[{"role": "system", "content": system_prompt}] + trimmed,
                        stream=True,
                        stream_options={"include_usage": True},
                        **kwargs,
                    )
                    break
                except Exception as e:
                    kind = classify_error(e)
                    if kind == "retry" and attempt < 3:
                        yield {"type": "retry", "attempt": attempt + 1, "wait": delay}
                        time.sleep(delay)
                        delay *= 2
                    elif kind == "no_tools" and _tools_ok:
                        _tools_ok = False
                        yield {
                            "type": "notice",
                            "content": "This model doesn't support tools, so it can only chat. "
                                       "Run `yamin --setup` to pick a different model.",
                        }
                    else:
                        raise

            if stream is None:
                raise RuntimeError("Could not reach the provider after several attempts.")

            full_content = ""
            calls        = []
            by_index     = {}
            usage_data   = None

            for chunk in stream:
                # capture usage from the final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_data = chunk.usage

                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    full_content += delta.content
                    yield {"type": "stream_token", "token": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0
                        cur = by_index.get(idx)
                        # some providers reuse index 0 for several parallel calls,
                        # so a new id on the same index means a new call
                        if cur is None or (tc.id and cur["id"] and tc.id != cur["id"]):
                            cur = {"id": "", "name": "", "args": "", "extra": {}}
                            calls.append(cur)
                            by_index[idx] = cur
                        if tc.id:
                            cur["id"] = tc.id
                        fn = tc.function
                        if fn and fn.name:
                            cur["name"] = fn.name
                        if fn and fn.arguments:
                            cur["args"] += fn.arguments
                        # keep any provider-specific fields (e.g. Gemini's thought signature)
                        cur["extra"].update(getattr(tc, "model_extra", None) or {})

        except KeyboardInterrupt:
            yield {"type": "error", "content": "Interrupted by user."}
            return
        except Exception as e:
            yield {"type": "error", "content": friendly_error(e)}
            return

        steps += 1

        # emit usage info
        if usage_data:
            input_tokens  = getattr(usage_data, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage_data, "completion_tokens", 0) or 0
        else:
            input_tokens  = count_tokens(trimmed)
            output_tokens = len(full_content) // 4
        usage_info = track(config["model"], input_tokens, output_tokens)
        yield {"type": "usage", "data": usage_info}

        tool_calls = [c for c in calls if c["name"]]
        for c in tool_calls:
            if not c["id"]:
                c["id"] = f"call_{uuid.uuid4().hex[:12]}"

        if not tool_calls:
            messages.append({"role": "assistant", "content": full_content})
            yield {"type": "done", "content": full_content or "✓ Done"}
            return

        messages.append({
            "role": "assistant",
            "content": full_content or None,
            "tool_calls": [
                {
                    **tc["extra"],
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["args"] or "{}"},
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
                try:
                    result = cap_result(str(execute_tool(name, args)))
                except Exception as e:
                    result = f"Tool error: {e}"

            yield {"type": "tool_result", "name": name, "result": result, "args": args}

            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result,
            })

    yield {"type": "max_steps"}