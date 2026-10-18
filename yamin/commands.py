import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yamin.tools import TOOL_DEFINITIONS
from yamin.usage import session_totals

console = Console(highlight=False)

COMMANDS = {
    "/help":    "Show all available commands",
    "/tools":   "List all tools the agent can use",
    "/history": "Show current session message count",
    "/usage":   "Show session token usage and cost",
    "/undo":    "Discard uncommitted changes (back to last commit)",
    "/clear":   "Clear the session and start fresh",
    "/exit":    "Exit the agent",
}


def handle_command(cmd: str, messages: list) -> str:
    """Returns 'exit', 'clear', or 'continue'"""
    cmd = cmd.strip().lower()

    if cmd == "/help":
        t = Table(show_header=False, box=None, padding=(0, 2))
        for name, desc in COMMANDS.items():
            t.add_row(f"[bold green]{name}[/bold green]", f"[dim]{desc}[/dim]")
        console.print(Panel(t, title="[bold]Commands[/bold]", expand=False))

    elif cmd == "/tools":
        t = Table(show_header=False, box=None, padding=(0, 2))
        for d in TOOL_DEFINITIONS:
            fn = d["function"]
            t.add_row(
                f"[bold cyan]{fn['name']}[/bold cyan]",
                f"[dim]{fn.get('description', '')[:70]}[/dim]",
            )
        console.print(Panel(t, title="[bold]Tools[/bold]", expand=False))

    elif cmd == "/history":
        console.print(f"  [dim]Session has {len(messages)} messages[/dim]")

    elif cmd == "/usage":
        totals = session_totals()
        console.print(
            f"  [dim]↑ {totals.get('input_tokens', 0)} in  "
            f"↓ {totals.get('output_tokens', 0)} out  "
            f"${totals.get('cost', 0):.4f} total[/dim]"
        )

    elif cmd == "/undo":
        answer = console.input(
            "  [yellow]This discards all uncommitted changes. Continue?[/yellow] [dim](y/n)[/dim] "
        ).strip().lower()
        if answer == "y":
            try:
                result = subprocess.run(
                    ["git", "checkout", "."], capture_output=True, text=True
                )
                if result.returncode == 0:
                    console.print("  [green]restored last committed state[/green]")
                else:
                    console.print(f"  [red]{result.stderr.strip()}[/red]")
            except Exception as e:
                console.print(f"  [red]{e}[/red]")
        else:
            console.print("  [dim]cancelled[/dim]")

    elif cmd == "/clear":
        return "clear"

    elif cmd == "/exit":
        return "exit"

    else:
        console.print(f"  [red]Unknown command: {cmd}[/red]  [dim]type /help[/dim]")

    return "continue"