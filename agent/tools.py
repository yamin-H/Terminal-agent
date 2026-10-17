# agent/tools.py
import subprocess
from pathlib import Path

def read_file(path: str) -> str:
    """Read and return the contents of a file.

    Args:
        path: Relative path to the file to read.

    Returns:
        The file's text content, or an error message on failure.
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {e}"

def write_file(path: str, content: str) -> str:
    try:
        Path(path).write_text(content)
        return "Done"
    except Exception as e:
        return f"Error: {e}"

import difflib

def edit_file(path: str, old_content: str, new_content: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8")
        if old_content not in text:
            return "Error: old_content not found in file. Read the file first and make sure it matches exactly."
        updated = text.replace(old_content, new_content, 1)
        Path(path).write_text(updated, encoding="utf-8")

        diff = list(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            lineterm=""
        ))
        return "DIFF\n" + "\n".join(diff) if diff else "Done (no changes)"
    except Exception as e:
        return f"Error: {e}"


def search_code(pattern: str, path: str = ".") -> str:
    try:
        matches = []
        for file in Path(path).rglob("*.py"):
            if any(p in file.parts for p in ["venv", "__pycache__"]):
                continue
            lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, line in enumerate(lines, 1):
                if pattern in line:
                    matches.append(f"{file}:{i}: {line.strip()}")
        return "\n".join(matches) if matches else "No matches found."
    except Exception as e:
        return f"Error: {e}"

def list_directory(path: str = ".") -> str:
    try:
        entries = list(Path(path).iterdir())
        return "\n".join(str(e) for e in entries)
    except Exception as e:
        return f"Error: {e}"

def run_command(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "search_code": search_code,
    "list_directory": list_directory,
    "run_command": run_command,
}

def execute_tool(name: str, args: dict) -> str:
    if name not in TOOLS:
        return f"Unknown tool: {name}"
    return TOOLS[name](**args)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "search_code",
        "description": "Search for a pattern across all Python files in the repo. Use this before reading files to find where something is defined or used.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The text or pattern to search for"},
                "path": {"type": "string", "description": "Directory to search in. Defaults to current directory."}
            },
            "required": ["pattern"]
        }
    }
},
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the directory"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"}
                },
                "required": ["command"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Edit a specific part of a file by replacing old_content with new_content. Always read the file first to get the exact content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file"},
                "old_content": {"type": "string", "description": "The exact text to replace"},
                "new_content": {"type": "string", "description": "The text to replace it with"}
            },
            "required": ["path", "old_content", "new_content"]
        }
    }
},
]