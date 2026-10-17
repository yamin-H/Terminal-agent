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

def run_loop(task: str, system_prompt: str):
    messages = [{"role": "user", "content": task}]
    steps = 0

    while steps < MAX_STEPS:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + messages,
            tools=TOOL_DEFINITIONS,
        )

        message = response.choices[0].message
        steps += 1

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = execute_tool(name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    return "Max steps reached."