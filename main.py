# main.py
import typer
from rich.console import Console
from rich.panel import Panel
from agent.loop import run_loop
from agent.prompt import SYSTEM_PROMPT

app = typer.Typer()
console = Console()

@app.command()
def run(task: str = typer.Argument(..., help="Task for the agent")):
    console.print(Panel(f"[bold green]Task:[/bold green] {task}", expand=False))
    
    with console.status("[bold yellow]Agent is working...[/bold yellow]"):
        result = run_loop(task, SYSTEM_PROMPT)
    
    console.print(Panel(f"[bold blue]Done:[/bold blue] {result}", expand=False))

if __name__ == "__main__":
    app()