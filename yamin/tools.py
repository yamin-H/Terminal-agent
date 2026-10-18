import difflib
import subprocess
from pathlib import Path

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
    ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ".html", ".htm",
    ".css", ".scss", ".sass", ".less", ".json", ".yaml", ".yml", ".toml",
    ".xml", ".csv", ".sql", ".md", ".txt", ".rst", ".ini", ".cfg", ".conf",
    ".env", ".gitignore", ".dockerignore", ".editorconfig", ".vue", ".svelte",
    ".astro", ".r", ".R", ".jl", ".lua", ".pl", ".pm", ".ex", ".exs",
    ".erl", ".hs", ".ml", ".clj", ".dart", ".tf", ".proto", ".graphql",
    ".dockerfile", "Makefile", "Dockerfile", "Jenkinsfile",
}

SKIP_DIRS = {"venv", ".venv", "__pycache__", "node_modules", ".git", "dist", "build"}


def read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {e}"

def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return "Done"
    except Exception as e:
        return f"Error: {e}"


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
        root = Path(path)
        for file in sorted(root.rglob("*")):
            if any(p in file.parts for p in SKIP_DIRS):
                continue
            if file.suffix not in TEXT_EXTENSIONS and file.name not in TEXT_EXTENSIONS:
                continue
            if not file.is_file():
                continue
            try:
                lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
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
            "description": "Search for a text pattern across all source and config files in the repo. Use this before reading files to find where something is defined or used.",
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
            "description": "Write content to a file. Creates the file and parent directories if they don't exist.",
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