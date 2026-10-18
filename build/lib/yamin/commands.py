from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from yamin.usage import session_totals

console = Console()

COMMANDS = {
    "/help":    "Show all available commands",
    "/tools":   "List all tools the agent can use",
    "/history": "Show current session message count",
    "/usage":   "Show session token usage and cost",
    "/undo":    "Restore last git committed state",
    "/clear":   "Clear the session and start fresh",
    "/exit":    "Exit the agent",
}

def handle_command(cmd: str, messages: list) -> str:
    """Returns 'exit', 'clear', or 'continue'"""

    if cmd == "/help":
        t = Table(show_header=False, box=None, padding=(0, 2))
        for name, desc in COMMANDS.items():
            t.add_row(f"[bold green]{name}[/bold green]", f"[dim]{desc}[/dim]")
        console.print(Panel(t, title="[bold]Commands[/bold]", expand=False))

    elif cmd == "/tools":
        from agent.tools import TOOLS
        t = Table(show_header=False, box=None, padding=(0, 2))
        for name in TOOLS:
            t.add_row(f"[bold cyan]{name}[/bold cyan]")
        console.print(Panel(t, title="[bold]Available Tools[/bold]", expand=False))

    elif cmd == "/history":
        console.print(f"[dim]Session has {len(messages)} messages[/dim]")

    elif cmd == "/usage":
        totals = session_totals()
        console.print(
            f"[dim]↑ {totals['input_tokens']} in  "
            f"↓ {totals['output_tokens']} out  "
            f"${totals['cost']:.4f} total[/dim]"
        )

    elif cmd == "/undo":
        import subprocess
        try:
            result = subprocess.run(
                ["git", "checkout", "."],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print("[green]✔ Restored last committed state[/green]")
            else:
                console.print(f"[red]✖ {result.stderr.strip()}[/red]")
        except Exception as e:
            console.print(f"[red]✖ {e}[/red]")

    elif cmd == "/clear":
        return "clear"

    elif cmd == "/exit":
        return "exit"

    else:
        console.print(f"[red]Unknown command: {cmd}[/red]  [dim]type /help[/dim]")

    return "continue"