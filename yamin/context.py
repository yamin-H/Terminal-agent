from pathlib import Path

IGNORE = {".git", "venv", "__pycache__", "node_modules", ".egg-info", "dist"}

def build_repo_context(root: str = ".") -> str:
    root_path = Path(root).resolve()
    lines = [f"Project root: {root_path}\n", "File structure:"]

    for path in sorted(root_path.rglob("*")):
        if any(p in IGNORE for p in path.parts):
            continue
        rel = path.relative_to(root_path)
        depth = len(rel.parts) - 1
        indent = "  " * depth
        lines.append(f"{indent}{'📁' if path.is_dir() else '📄'} {rel}")

    return "\n".join(lines)