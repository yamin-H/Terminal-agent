import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.syntax import Syntax
from agent.loop import run_loop
from agent.prompt import SYSTEM_PROMPT
from agent.context import build_repo_context
from agent.session import save_session, load_session, clear_session

app = typer.Typer()
console = Console()

TOOL_COLORS = {
    "read_file": "cyan",
    "write_file": "yellow",
    "edit_file": "yellow",
    "list_directory": "blue",
    "run_command": "magenta",
    "search_code": "green",
}

def render_events(task, messages):
    live = None
    stream_live = None
    streamed_text = ""

    def stop_spinner():
        nonlocal live
        if live:
            live.stop()
            live = None

    def stop_stream():
        nonlocal stream_live, streamed_text
        if stream_live:
            stream_live.stop()
            stream_live = None
        streamed_text = ""

    gen = run_loop(task, SYSTEM_PROMPT, messages)
    event = next(gen)

    while True:
        if event["type"] == "thinking":
            stop_stream()
            live = Live(
                Spinner("dots", text=Text("thinking...", style="dim")),
                refresh_per_second=20,
                transient=True
            )
            live.start()
            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif event["type"] == "stream_token":
            stop_spinner()
            streamed_text += event["token"]
            if stream_live is None:
                stream_live = Live(
                    Panel(streamed_text, title="[bold blue]Assistant[/bold blue]", border_style="blue"),
                    refresh_per_second=20
                )
                stream_live.start()
            else:
                stream_live.update(
                    Panel(streamed_text, title="[bold blue]Assistant[/bold blue]", border_style="blue")
                )
            try:
                event = gen.send(None)
            except StopIteration:
                stop_stream()
                break

        elif event["type"] == "tool_call":
            stop_spinner()
            stop_stream()
            name = event["name"]
            args = event["args"]
            color = TOOL_COLORS.get(name, "white")
            args_str = "  ".join(f"[dim]{k}=[/dim][italic]{v}[/italic]" for k, v in args.items())
            console.print(f"  [bold {color}]▶ {name}[/bold {color}]  {args_str}")

            if event["needs_approval"]:
                answer = console.input(f"  [bold yellow]Allow {name}? (y/n):[/bold yellow] ").strip().lower()
                approval = "approved" if answer == "y" else "denied"
                if approval == "denied":
                    console.print("  [dim red]✖ Denied[/dim red]\n")
            else:
                approval = "approved"

            try:
                event = gen.send(approval)
            except StopIteration:
                break

        elif event["type"] == "tool_result":
            name = event["name"]
            result = event["result"]

            if name == "edit_file" and result.startswith("DIFF"):
                diff_body = "\n".join(result.split("\n")[1:])
                console.print(Syntax(diff_body, "diff", theme="monokai", indent_guides=False))
                console.print()

            elif name == "read_file":
                syntax = Syntax(result, "python", theme="monokai", line_numbers=True, word_wrap=True)
                console.print(Panel(syntax, title="[dim]file content[/dim]", border_style="dim"))
                console.print()

            elif name == "run_command":
                console.print(Panel(result.strip(), title="[dim]output[/dim]", border_style="dim yellow"))
                console.print()

            elif name == "list_directory":
                for line in result.strip().split("\n"):
                    console.print(f"  [dim]•[/dim] {line}")
                console.print()

            else:
                preview = result[:200].replace("\n", " ") + ("..." if len(result) > 200 else "")
                console.print(f"  [dim green]↳ {preview}[/dim green]")
                console.print()

            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif event["type"] == "done":
            stop_spinner()
            stop_stream()
            console.print(Rule("[dim green]✓ done[/dim green]", style="dim"))
            console.print()
            break

        elif event["type"] == "error":
            stop_spinner()
            stop_stream()
            console.print(f"\n[red]✖ Error: {event['content']}[/red]\n")
            break

        elif event["type"] == "max_steps":
            stop_spinner()
            stop_stream()
            console.print("[red]⚠ Max steps reached.[/red]")
            break

        else:
            try:
                event = gen.send(None)
            except StopIteration:
                break


@app.command()
def run():
    console.print()
    console.print(Panel(
        "[bold green]Terminal Coding Agent[/bold green]\n[dim]Type your task and press Enter. Type 'exit' to quit. Type 'clear' to reset session.[/dim]",
        expand=False
    ))
    console.print()

    saved = load_session()
    if saved:
        messages = saved
        console.print(f"[dim]✓ Resumed previous session ({len(messages)} messages)[/dim]\n")
    else:
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
            save_session(messages)
            break

        if not task:
            continue

        if task == "exit":
            save_session(messages)
            break

        if task == "clear":
            clear_session()
            messages = []
            console.print("[dim]✓ Session cleared[/dim]\n")
            continue

        render_events(task, messages)
        save_session(messages)


if __name__ == "__main__":
    run()