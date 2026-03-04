# OpenClaw LLM Auto-Heal Cron

This repo contains two PowerShell scripts for OpenClaw model auto-heal scheduling:

- `scripts/llm-auto-heal.ps1`
  - Detects recent LLM-related errors from OpenClaw logs.
  - Probes available models and selects the best healthy preferred model.
  - Switches model when needed and restarts gateway.
  - Emits run summary line: `MODEL_SWITCHED: ...` for cron run results.

- `scripts/setup-llm-auto-heal-cron.ps1`
  - One-shot setup/update for OpenClaw cron job.
  - Ensures a single 30-minute cron schedule.
  - Sets timeout (default 900s).
  - Optional: disable duplicate Windows Task Scheduler tasks that run the same script.

## Quick Start (Windows)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\scripts\\setup-llm-auto-heal-cron.ps1" -DisableWindowsTask
```

## Optional Parameters

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\scripts\\setup-llm-auto-heal-cron.ps1" \
  -IntervalMinutes 30 \
  -TimeoutSeconds 900 \
  -JobName "OpenClaw LLM Auto Heal" \
  -AgentId "main" \
  -SessionTarget "isolated"
```

## Verification

```powershell
openclaw cron list --json
openclaw cron runs --id <job-id> --limit 5
```

Look for `MODEL_SWITCHED:` in run output / summaries.
