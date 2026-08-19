
# TJM Project - Grounding Agent

An automation agent that visually locates and interacts with desktop UI elements (icons, buttons, dialogs) using a VLM-based grounding pipeline, then drives a Notepad workflow end-to-end: fetching blog posts from a public API, typing them into Notepad, and saving each one.


## Requirements
- Windows 10/11, 1920x1080 display
- Python 3.14+ (managed via uv)
- uv installed
- An Anthropic API key
- A Notepad shortcut icon created on the desktop before running (see below)

## Setup
1. Clone the repo and install dependencies:
```
git clone https://github.com/Laweeza/tjm-labs-grounding-agent.git
cd tjm-labs-grounding-agent
uv sync
```

2. Set Anthropic API Key:
```
setx ANTHROPIC_API_KEY "your-key-here"
```
or set for current session as seen below for PowerShell

```
$env:ANTHROPIC_API_KEY = "your-key-here"
```

3. Create Notepad desktop shortcut:
   - Right-click Desktop -> New -> Shortcut
   - Enter notepad.exe as the location
   - Name it "Notepad"


## Run
```
uv run main.py
```
This will:
1. Fetch first 10 posts from JSONPlaceholder
2. For each post: locate Notepad desktop icon, launch, type the post content, save it as ```post_{id}.txt``` to ```Desktop/tjm-project/```, and close Notepad
3. Re-screenshot and re-locate the icon fresh before each launch.

Logs printed, including grounding confidence

## Commands

| Task | Command |
|---|---|
|Run workflow | uv run main.py
|Demo on other icon | uv run python demo_grounding.py "the Recycle Bin desktop icon" -- click or uv run demo_grounding.py "the Microsoft Edge desktop icon" --click
|Run Unit Tests | run pytest -v
| Script to annotate screenshot | uv run python scripts/annotate_screenshots.py
| Script to inject popups throughout workflow | uv run python scripts/popup_random_injections.py 


### Project Structure

```
tjm-labs-grounding-agent/
├── screenshots/  
├── src/
│   └── tjm_labs_grounding_agent/
│       ├── capture.py       # Screenshot capture
│       ├── grounding.py     # VLM-based visual grounding (coarse pass + ReGround refinement)
│       ├── actions.py       # Mouse/keyboard actions, window focus, save/close helpers
│       ├── popup.py         # Generic popup/obstruction detection and recovery
│       ├── api_client.py    # JSONPlaceholder fetch + post formatting
│       └── workflow.py      # End-to-end orchestration for the Notepad task
├── scripts/
│   ├── annotate_screenshots.py
|   └── popup_injection.py
├── tests/
│   ├── test_grounding.py
|   └── test_popup.py
├── main.py                  # CLI entry point
├── demo_grounding.py        # Standalone demo of grounding on arbitrary targets           # Annotated screenshot deliverables
├── pyproject.toml
├── uv.lock
├── README.md
├── designchart.md
└── DESIGN.md
```


## Screenshots
- Annotated screenshots demonstrating detection at multiple icon positions in ```screenshots/```

See [DESIGN.md](./DESIGN.md) for architecture, grounding strategy and tradeoffs

