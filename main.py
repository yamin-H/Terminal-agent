"""Terminal Coding Agent entry point"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from agent.loop import run_loop
from agent.prompt import SYSTEM_PROMPT
from agent.context import build_repo_context

app = typer.Typer()
console = Console()

TOOL_COLORS = {
    "read_file": "cyan",
    "write_file": "yellow",
    "edit_file": "yellow",
    "search_code": "green",
    "list_directory": "blue",
    "run_command": "magenta",
}

def render_events(task, messages):
    live = None

    def stop_spinner():
        nonlocal live
        if live:
            live.stop()
            live = None

    for event in run_loop(task, SYSTEM_PROMPT, messages):
        if event["type"] == "thinking":
            live = Live(Spinner("dots", text=Text("thinking...", style="dim")), refresh_per_second=20, transient=True)
            live.start()

        elif event["type"] == "tool_call":
            stop_spinner()
            name = event["name"]
            args = event["args"]
            color = TOOL_COLORS.get(name, "white")
            args_str = "  ".join(f"[dim]{k}=[/dim][italic]{v}[/italic]" for k, v in args.items())
            console.print(f"  [bold {color}]▶ {name}[/bold {color}]  {args_str}")

        elif event["type"] == "tool_result":
            result = event["result"]
            preview = result[:120].replace("\n", " ") + ("..." if len(result) > 120 else "")
            console.print(f"  [dim green]↳ {preview}[/dim green]")
            console.print()

        elif event["type"] == "done":
            stop_spinner()
            console.print(Rule(style="dim"))
            console.print(Panel(f"[white]{event['content']}[/white]", title="[bold blue]Done[/bold blue]"))
            console.print()

        elif event["type"] == "max_steps":
            stop_spinner()
            console.print("[red]⚠ Max steps reached.[/red]")

@app.command()
def run():
    console.print()
    console.print(Panel("[bold green]Terminal Coding Agent[/bold green]\n[dim]Type your task and press Enter. Type 'exit' to quit.[/dim]", expand=False))
    console.print()

    with console.status("[dim]Loading repo context...[/dim]", spinner="dots"):
        context = build_repo_context(".")

    messages = [
        {
            "role": "user",
            "content": f"Here is the current project structure:\n\n{context}"
        },
        {
            "role": "assistant",
            "content": "Got it. I have the project structure loaded and I'm ready to help."
        }
    ]

    console.print("[dim]✓ Repo context loaded[/dim]\n")

    while True:
        try:
            task = console.input("[bold green]>[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not task:
            continue

        if task.lower() in ("exit", "quit"):
            console.print("[dim]Bye.[/dim]")
            break

        console.print()
        render_events(task, messages)

if __name__ == "__main__":
    app()