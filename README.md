# myopenclaw

Personal OpenClaw automation scripts, organized by **task** for reuse.

## Repository layout

```text
myopenclaw/
  tasks/
    index.md
    llm-auto-heal/
      scripts/
      docs/
      README.md
    _template/
      README.md
      task.meta.json
  tools/
    new-task.ps1
```

## Current tasks

- See `tasks/index.md`

## Create a new task quickly

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\new-task.ps1" -Name "example-task" -Owner "lijing"
```

Then fill task docs and append a row in `tasks/index.md`.

## Skills

- Skills mirror: `skills/`
- Skills list: `skills/index.md`
- Resync helper: `tools/sync-skills.ps1`
