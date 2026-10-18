import json
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from prompt_toolkit import Application, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

console = Console(highlight=False)

CONFIG_DIR  = Path.home() / ".yamin"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = {
    "groq":        {"label": "Groq",             "base_url": "https://api.groq.com/openai/v1"},
    "openai":      {"label": "OpenAI",           "base_url": "https://api.openai.com/v1"},
    "gemini":      {"label": "Google Gemini",    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"},
    "anthropic":   {"label": "Anthropic Claude", "base_url": "https://api.anthropic.com/v1/"},
    "huggingface": {"label": "Hugging Face",     "base_url": "https://router.huggingface.co/v1"},
    "custom":      {"label": "Other (any OpenAI-compatible URL, e.g. Ollama, OpenRouter)", "base_url": ""},
}

# model types that can't be used for chat
SKIP = ("whisper", "tts", "embed", "guard", "moderation", "dall-e",
        "image", "transcribe", "audio", "realtime")

select_style = Style.from_dict({
    "title":  "bold",
    "hint":   "#6b7280",
    "filter": "#0066ff",
    "sel":    "#0066ff bold",
    "opt":    "#9ca3af",
    "dim":    "#6b7280",
})


def first_run() -> bool:
    return not CONFIG_FILE.exists()


def fetch_models(base_url: str, api_key: str) -> list:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
        ids = [m.id.removeprefix("models/") for m in client.models.list()]
    except Exception:
        return []
    return sorted(i for i in ids if not any(s in i.lower() for s in SKIP))


def select(title: str, options: list, allow_custom: bool = False, page: int = 10) -> str:
    """Arrow-key selector. Type to filter. Enter to choose."""
    state = {"i": 0, "q": ""}

    def visible() -> list:
        q = state["q"].lower()
        return [o for o in options if q in o.lower()] if q else options

    def render():
        items = visible()
        out = [("class:title", f"  {title}"), ("class:hint", "   ↑/↓ move · enter select · type to filter\n")]
        if state["q"]:
            out.append(("class:filter", f"  filter: {state['q']}\n"))
        out.append(("", "\n"))

        if not items:
            msg = f"  no match, press enter to use '{state['q']}' as the id" if allow_custom else "  no match"
            out.append(("class:dim", msg + "\n"))
            return out

        i     = min(state["i"], len(items) - 1)
        start = max(0, min(i - page // 2, len(items) - page))
        for n, item in enumerate(items[start:start + page], start):
            if n == i:
                out.append(("class:sel", f"  ❯ {item}\n"))
            else:
                out.append(("class:opt", f"    {item}\n"))
        if len(items) > page:
            out.append(("class:dim", f"\n  {i + 1}/{len(items)}\n"))
        return out

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        n = len(visible())
        if n:
            state["i"] = (min(state["i"], n - 1) - 1) % n

    @kb.add("down")
    def _(event):
        n = len(visible())
        if n:
            state["i"] = (min(state["i"], n - 1) + 1) % n

    @kb.add("enter")
    def _(event):
        items = visible()
        if items:
            event.app.exit(result=items[min(state["i"], len(items) - 1)])
        elif allow_custom and state["q"]:
            event.app.exit(result=state["q"])

    @kb.add("backspace")
    def _(event):
        state["q"] = state["q"][:-1]
        state["i"] = 0

    @kb.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @kb.add("<any>")
    def _(event):
        ch = event.data
        if ch and ch.isprintable():
            state["q"] += ch
            state["i"] = 0

    app = Application(
        layout=Layout(Window(FormattedTextControl(render, show_cursor=False), wrap_lines=False)),
        key_bindings=kb,
        style=select_style,
        erase_when_done=True,
    )
    return app.run()


def run_setup():
    console.print()
    console.print("  [bold white on #0066ff]  Y A M I N  [/bold white on #0066ff]  [dim]setup[/dim]")
    console.print()

    labels   = {v["label"]: k for k, v in PROVIDERS.items()}
    label    = select("Select a provider", list(labels))
    provider = labels[label]
    info     = PROVIDERS[provider]
    name     = label.split(" (")[0]
    console.print(f"  [dim]provider[/dim]  {name}")

    base_url = info["base_url"]
    if provider == "custom":
        console.print()
        base_url = prompt("  Base URL (e.g. http://localhost:11434/v1) › ").strip()
        if not base_url:
            console.print("  [red]Base URL required.[/red]")
            raise SystemExit(1)

    console.print()
    api_key = prompt(f"  {name} API key › ", is_password=True).strip()
    if not api_key:
        if provider == "custom":
            api_key = "none"
        else:
            console.print("  [red]API key required.[/red]")
            raise SystemExit(1)

    console.print("\n  [dim]Fetching available models...[/dim]")
    models = fetch_models(base_url, api_key)

    if models:
        model = select("Select a model", models, allow_custom=True)
    else:
        console.print("  [yellow]Couldn't fetch the model list (wrong key, or this provider doesn't list models).[/yellow]")
        model = prompt("  Model id › ").strip()
        if not model:
            console.print("  [red]Model id required.[/red]")
            raise SystemExit(1)
    console.print(f"  [dim]model[/dim]     {model}")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({
        "provider":    provider,
        "base_url":    base_url,
        "api_key":     api_key,
        "model":       model,
        "max_steps":   30,
        "max_tokens":  4000 if provider == "groq" else 30000,
        "risky_tools": ["write_file", "edit_file", "run_command"],
    }, indent=2))
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass

    console.print()
    console.print(f"  [green]✔[/green] Saved to [dim]{CONFIG_FILE}[/dim]")
    console.print()
    console.print("  [dim]Run [white]yamin[/white] to start. Run [white]yamin --setup[/white] to change provider or model.[/dim]")
    console.print()


def load_user_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (OSError, ValueError):
        return {}