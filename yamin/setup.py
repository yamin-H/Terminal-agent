import json
from pathlib import Path
from rich.console import Console
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML

console = Console()

CONFIG_DIR  = Path.home() / ".yamin"
CONFIG_FILE = CONFIG_DIR / "config.json"

MODELS = [
    ("1", "qwen/qwen3.8-27b",                    "Qwen3.8-27b — best quality"),
    ("2", "meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout — fast"),
    ("3", "llama-3.1-8b-instant",              "Llama 3.1 8B — fastest"),
]

def first_run() -> bool:
    return not CONFIG_FILE.exists()

def run_setup():
    console.print()
    console.print("  [bold white on #0066ff]  Y A M I N  [/bold white on #0066ff]  [dim]first time setup[/dim]")
    console.print()
    console.print("  [dim]Let's get you set up in 30 seconds.[/dim]")
    console.print()

    # API key
    api_key = prompt("  Groq API key › ", is_password=True).strip()
    if not api_key:
        console.print("[red]✖ API key required.[/red]")
        raise SystemExit(1)

    # Model selection
    console.print()
    console.print("  [dim]Select a model:[/dim]")
    console.print()
    for num, model_id, label in MODELS:
        console.print(f"  [bold white]{num}[/bold white]  [dim]{label}[/dim]")
    console.print()

    choice = prompt("  Model (1/2/3) › ").strip()
    model  = next((m for n, m, _ in MODELS if n == choice), MODELS[0][1])

    # Save config
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({
        "groq_api_key": api_key,
        "model":        model,
        "max_steps":    30,
        "max_tokens":   100000,
        "risky_tools":  ["write_file", "edit_file", "run_command"],
    }, indent=2))

    console.print()
    console.print(f"  [green]✔[/green] Config saved to [dim]{CONFIG_FILE}[/dim]")
    console.print(f"  [green]✔[/green] Model set to [blue]{model}[/blue]")
    console.print()
    console.print("  [dim]Run [white]yamin[/white] again to start.[/dim]")
    console.print()

def load_user_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())