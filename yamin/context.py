import os
from pathlib import Path

IGNORE_DIRS = {
    ".git", "venv", ".venv", "env", "__pycache__", "node_modules",
    "dist", "build", ".next", ".idea", ".vscode", ".pytest_cache",
    ".mypy_cache", "target", "coverage",
}
IGNORE_SUFFIXES = (".egg-info", ".pyc", ".lock", ".log")
MAX_CHARS = 8000


def build_repo_context(root: str = ".") -> str:
    root_path = Path(root).resolve()
    lines = [f"Project root: {root_path}", "File structure:"]
    size = sum(len(l) for l in lines)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORE_DIRS and not d.endswith(IGNORE_SUFFIXES)
        )
        rel   = Path(dirpath).relative_to(root_path)
        depth = 0 if str(rel) == "." else len(rel.parts)
        indent = "  " * depth

        if depth:
            lines.append(f"{indent[:-2]}{rel.name}/")

        for f in sorted(filenames):
            if f.endswith(IGNORE_SUFFIXES):
                continue
            line = f"{indent}{f}"
            size += len(line) + 1
            if size > MAX_CHARS:
                lines.append("... (truncated, use list_directory to explore)")
                return "\n".join(lines)
            lines.append(line)

    return "\n".join(lines)