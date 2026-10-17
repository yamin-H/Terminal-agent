import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agent.tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MAX_STEPS = 30

def run_loop(task: str, system_prompt: str, messages: list = None):
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": task})
    steps = 0

    while steps < MAX_STEPS:
        yield {"type": "thinking"}

        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[{"role": "system", "content": system_prompt}] + messages,
                tools=TOOL_DEFINITIONS,
            )
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            return

        message = response.choices[0].message
        steps += 1

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            yield {"type": "done", "content": message.content}
            return

        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            yield {"type": "tool_call", "name": name, "args": args}

            result = execute_tool(name, args)

            yield {"type": "tool_result", "name": name, "result": result}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    yield {"type": "max_steps"}