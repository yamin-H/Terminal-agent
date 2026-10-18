<h1 align="center">yamin</h1>

<p align="center">
  A fast, minimal AI coding agent for your terminal.<br>
  Ask it to read, search, edit and run things in any project, with you in control.
</p>

<p align="center">
  <a href="https://pypi.org/project/yamin/"><img alt="PyPI" src="https://img.shields.io/pypi/v/yamin?color=0066ff"></a>
  <img alt="Python" src="https://img.shields.io/pypi/pyversions/yamin?color=0066ff">
  <img alt="License" src="https://img.shields.io/pypi/l/yamin?color=0066ff">
</p>

<!-- Add a screenshot or GIF of yamin in action here -->
<!-- ![yamin demo](docs/demo.gif) -->

---

## Features

- **Works inside any repo.** Run `yamin` in a project folder and it indexes that project's structure automatically.
- **Real tools, not just chat.** Read files, list directories, search code, edit and write files, and run shell commands.
- **You approve every risky action.** Writing, editing and running commands always ask for your confirmation first.
- **Clear diffs.** File edits are shown as syntax-highlighted diffs before you move on.
- **Streaming markdown output.** Responses render live with headings, lists and code blocks.
- **Bring your own model.** Pick from built-in presets or enter any model id supported by your provider.
- **Session memory.** Your conversation resumes where you left off, per project.
- **Cost visibility.** Token usage and running cost are shown after each turn.

## Installation

The recommended way is [pipx](https://pipx.pypa.io), which keeps yamin isolated and puts the `yamin` command on your PATH:

```bash
pipx install yamin
```

Or with pip:

```bash
pip install yamin
```

Requires Python 3.10 or newer.

## Quick start

```bash
cd your-project
yamin
```

On first run, yamin walks you through a short setup:

1. Paste your [Groq API key](https://console.groq.com/keys).
2. Choose a model, or enter your own model id.

Then run `yamin` again and start asking:

```
❯ explain how authentication works in this project
❯ fix the failing tests
❯ add input validation to the signup endpoint
```

## Commands

- `/help` shows all available commands
- `/clear` clears the conversation and re-indexes the project
- `/exit` saves the session and quits

You can also press `Ctrl+C` at the prompt to save and exit.

## Tools

- `list_directory` lists files and folders
- `read_file` reads a file
- `search_code` searches across the codebase
- `edit_file` applies a targeted edit and shows the diff (asks approval)
- `write_file` creates or overwrites a file (asks approval)
- `run_command` runs a shell command (asks approval)

## Configuration

Settings are stored in `~/.yamin/config.json`. You can edit this file directly:

- `groq_api_key` is your API key
- `model` is the model id used for all requests
- `max_steps` is the maximum number of tool steps per task (default `30`)
- `max_tokens` is the context size before older messages are trimmed (default `100000`)
- `risky_tools` is the list of tools that require your approval

To change your key or model, edit the file, or delete it and run `yamin` again to repeat the setup.

## Privacy and safety

- Your API key and settings stay on your machine, in `~/.yamin/`.
- Requests go directly from your machine to the model provider using your own key. yamin has no server and collects no telemetry.
- The contents of files the agent reads are sent to the model provider as part of the conversation. Avoid running yamin in folders that contain secrets you don't want shared.
- The session is saved in the folder where you run `yamin`. Add the session file to that project's `.gitignore`.

## Development

```bash
git clone https://github.com/<your-username>/yamin
cd yamin
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -e .
yamin
```

## Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like to change.

## License

MIT © Yamin Hossain