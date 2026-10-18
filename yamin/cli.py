import shutil
import subprocess
import sys
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.padding import Padding
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from yamin.commands import handle_command
from yamin.config import load_config
from yamin.context import build_repo_context
from yamin.loop import run_loop
from yamin.prompt import SYSTEM_PROMPT
from yamin.session import clear_session, load_session, save_session
from yamin.usage import session_totals
from yamin.setup import first_run, run_setup

config = load_config()

console = Console(
    highlight=False,
    theme=Theme({
        "markdown.code":        "#79c0ff",
        "markdown.code_block":  "#c9d1d9",
        "markdown.h1":          "bold #0066ff",
        "markdown.h2":          "bold #0066ff",
        "markdown.h3":          "bold white",
        "markdown.item.bullet": "#0066ff",
    }),
)

TOOL_COLORS = {
    "read_file":      "cyan",
    "write_file":     "yellow",
    "edit_file":      "yellow",
    "list_directory": "blue",
    "run_command":    "magenta",
    "search_code":    "green",
}

# ── helpers ────────────────────────────────────────────────────────────────────

def get_git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "no-git"


def seed_messages() -> list:
    context = build_repo_context(".")
    return [
        {"role": "user",      "content": f"Project structure:\n\n{context}"},
        {"role": "assistant", "content": "Ready."},
    ]

# ── welcome ────────────────────────────────────────────────────────────────────

def print_welcome():
    branch = get_git_branch()
    model  = config["model"].split("/")[-1]
    console.print()
    console.print(f"  [bold #0066ff]yamin[/bold #0066ff]  [dim]{model} · {branch}[/dim]")
    console.print("  [dim]/help for commands · ctrl+c to exit[/dim]")
    console.print()

# ── input ──────────────────────────────────────────────────────────────────────

pt_style = Style.from_dict({
    "prompt":         "#0066ff bold",
    "bottom-toolbar": "noreverse #2f3542",
    "status":         "noreverse #6b7280",
})

session = PromptSession(
    style=pt_style,
    erase_when_done=True,
    complete_in_thread=True,
)

def get_input(messages: list) -> str:
    w      = shutil.get_terminal_size().columns - 1
    totals = session_totals()
    cost   = f" · ${totals['cost']:.4f}" if totals["cost"] > 0 else ""
    model  = config["model"].split("/")[-1]
    status = f"  {model} · {get_git_branch()} · {len(messages)} msgs{cost}"

    return session.prompt(
        [("class:bottom-toolbar", "─" * w + "\n"), ("class:prompt", "❯ ")],
        placeholder='ask anything…  "fix the failing tests"',
        bottom_toolbar=[
            ("class:bottom-toolbar", "─" * w + "\n"),
            ("class:status", status),
        ],
    )

# ── render ─────────────────────────────────────────────────────────────────────

def reply_view(text: str):
    grid = Table.grid(padding=(0, 1))
    grid.add_column(width=1)
    grid.add_column()
    grid.add_row(Text("●", style="#0066ff"), Markdown(text))
    return Padding(grid, (0, 2))


def render_events(task: str, messages: list):
    live          = None
    stream_live   = None
    streamed_text = ""
    in_stream     = False

    def stop_spinner():
        nonlocal live
        if live:
            live.stop()
            live = None

    def flush_stream():
        nonlocal in_stream, streamed_text, stream_live
        if stream_live:
            stream_live.stop()
            stream_live = None
        if in_stream:
            console.print()
            in_stream     = False
            streamed_text = ""

    gen   = run_loop(task, SYSTEM_PROMPT, messages)
    event = next(gen)

    while True:
        t = event["type"]

        if t == "thinking":
            flush_stream()
            live = Live(
                Spinner("dots2", text=Text(" thinking", style="dim")),
                console=console,
                refresh_per_second=20,
                transient=True,
            )
            live.start()
            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif t == "stream_token":
            stop_spinner()
            streamed_text += event["token"]
            in_stream = True
            view = reply_view(streamed_text)
            if stream_live is None:
                stream_live = Live(
                    view,
                    console=console,
                    refresh_per_second=12,
                    vertical_overflow="visible",
                )
                stream_live.start()
            else:
                stream_live.update(view)
            try:
                event = gen.send(None)
            except StopIteration:
                flush_stream()
                break

        elif t == "tool_call":
            stop_spinner()
            flush_stream()
            name  = event["name"]
            color = TOOL_COLORS.get(name, "white")
            args  = ", ".join(
                escape(str(v).replace("\n", "↵")[:50]) for v in event["args"].values()
            )
            console.print(f"  [{color}]●[/{color}] [bold]{name}[/bold][dim]({args})[/dim]")

            if event["needs_approval"]:
                answer   = console.input("    [yellow]allow?[/yellow] [dim](y/n)[/dim] ").strip().lower()
                approval = "approved" if answer == "y" else "denied"
                if approval == "denied":
                    console.print("    [red]denied[/red]")
            else:
                approval = "approved"

            try:
                event = gen.send(approval)
            except StopIteration:
                break

        elif t == "tool_result":
            name   = event["name"]
            result = event["result"].strip()
            lines  = result.split("\n") if result else []

            if name == "edit_file" and result.startswith("DIFF"):
                diff_body = "\n".join(lines[1:])
                console.print(Padding(Syntax(diff_body, "diff", theme="monokai"), (0, 4)))
            else:
                limit = {"run_command": 8, "list_directory": 6, "search_code": 5}.get(name, 0)
                if limit:
                    for i, line in enumerate(lines[:limit]):
                        branch = "⎿" if i == 0 else " "
                        console.print(f"    [dim]{branch} {escape(line[:100])}[/dim]")
                    if len(lines) > limit:
                        console.print(f"      [dim]… +{len(lines) - limit} more[/dim]")
                else:
                    console.print(f"    [dim]⎿ {len(lines)} lines[/dim]")
            console.print()

            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif t == "usage":
            d = event["data"]
            console.print(
                f"  [dim]↑{d['input_tokens']} ↓{d['output_tokens']} · ${d['cost']:.4f}[/dim]\n"
            )
            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif t == "notice":
            stop_spinner()
            flush_stream()
            console.print(f"  [yellow]{escape(event['content'])}[/yellow]\n")
            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif t == "done":
            stop_spinner()
            flush_stream()
            break

        elif t == "error":
            stop_spinner()
            flush_stream()
            console.print(f"  [red]error:[/red] {escape(event['content'])}\n")
            break

        elif t == "retry":
            stop_spinner()
            console.print(
                f"  [yellow]rate limited[/yellow] [dim]· retrying in {event['wait']}s "
                f"(attempt {event['attempt']}/3)[/dim]"
            )
            try:
                event = gen.send(None)
            except StopIteration:
                break

        elif t == "max_steps":
            stop_spinner()
            flush_stream()
            console.print("  [yellow]max steps reached[/yellow]\n")
            break

        else:
            try:
                event = gen.send(None)
            except StopIteration:
                break

# ── entry ──────────────────────────────────────────────────────────────────────

def run():
    if first_run() or "--setup" in sys.argv:
        try:
            run_setup()
            clear_session()
        except (KeyboardInterrupt, EOFError):
            console.print("\n  [dim]setup cancelled[/dim]\n")
        return

    print_welcome()

    saved = load_session()
    if saved:
        messages = saved
        console.print(f"  [dim]resumed · {len(messages)} messages[/dim]\n")
    else:
        with console.status("  [dim]indexing repo...[/dim]", spinner="dots2"):
            messages = seed_messages()
        console.print("  [dim]repo indexed[/dim]\n")

    while True:
        try:
            task = get_input(messages).strip()
        except (KeyboardInterrupt, EOFError):
            save_session(messages)
            console.print("\n  [dim]session saved[/dim]\n")
            break

        if not task:
            continue

        if task.startswith("/") or task.lower() == "clear":
            result = handle_command(task if task.startswith("/") else "/clear", messages)
            if result == "exit":
                save_session(messages)
                break
            elif result == "clear":
                clear_session()
                with console.status("  [dim]indexing repo...[/dim]", spinner="dots2"):
                    messages = seed_messages()
                console.print("  [dim]session cleared[/dim]")
            continue

        if task.lower() in ("exit", "quit"):
            save_session(messages)
            break

        console.print(Padding(
            Text(f"❯ {task}", style="bold white"),
            (0, 2), style="on #1c2333", expand=True,
        ))
        console.print()
        render_events(task, messages)
        save_session(messages)


if __name__ == "__main__":
    run()