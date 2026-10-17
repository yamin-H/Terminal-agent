import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agent.tools import TOOL_DEFINITIONS, execute_tool
from agent.config import load_config

config = load_config()

MAX_STEPS = config["max_steps"]
RISKY_TOOLS = set(config["risky_tools"])

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


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
            stream = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "system", "content": system_prompt}] + trimmed,
                tools=TOOL_DEFINITIONS,
                stream=True,
            )

            full_content = ""
            tool_calls_acc = {}

            for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.content:
                    full_content += delta.content
                    yield {"type": "stream_token", "token": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        i = tc.index
                        if i not in tool_calls_acc:
                            tool_calls_acc[i] = {"id": tc.id, "name": tc.function.name or "", "args": ""}
                        if tc.function.name:
                            tool_calls_acc[i]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_acc[i]["args"] += tc.function.arguments

        except KeyboardInterrupt:
            yield {"type": "error", "content": "Interrupted by user."}
            return
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            return

        class FakeMessage:
            pass
        class FakeToolCall:
            pass
        class FakeFunc:
            pass

        message = FakeMessage()
        message.content = full_content if full_content else ""

        if tool_calls_acc:
            tcs = []
            for i in sorted(tool_calls_acc.keys()):
                t = FakeToolCall()
                t.id = tool_calls_acc[i]["id"]
                t.function = FakeFunc()
                t.function.name = tool_calls_acc[i]["name"]
                t.function.arguments = tool_calls_acc[i]["args"]
                tcs.append(t)
            message.tool_calls = tcs
        else:
            message.tool_calls = None

        steps += 1

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            yield {"type": "done", "content": message.content or "✓ Done"}
            return

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            needs_approval = name in RISKY_TOOLS

            approval = yield {"type": "tool_call", "name": name, "args": args, "needs_approval": needs_approval}

            if approval == "denied":
                result = "User denied this action."
            else:
                result = execute_tool(name, args)

            yield {"type": "tool_result", "name": name, "result": result}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    yield {"type": "max_steps"}