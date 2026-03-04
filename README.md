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

### One-command skills publish

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1"
```

Optional custom commit message:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -Message "chore(skills): weekly sync"
```

More options:

```powershell
# Preview only (no commit/push)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -DryRun

# Publish and create a tag
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -TagAfterPush

# Publish and create custom tag
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -TagAfterPush -TagName "skills-2026-03-04"
```
