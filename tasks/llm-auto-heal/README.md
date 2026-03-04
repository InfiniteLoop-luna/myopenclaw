# Task: llm-auto-heal

Auto-heal workflow for OpenClaw model failures.

## Files

- `scripts/llm-auto-heal.ps1`
  - Checks recent LLM-related errors
  - Probes model health
  - Switches to best healthy preferred model
  - Restarts gateway
  - Emits `MODEL_SWITCHED: ...` summary

- `scripts/setup-llm-auto-heal-cron.ps1`
  - Creates/updates OpenClaw cron job
  - Default: every 30 minutes, timeout 900s
  - Optional: disable duplicate Windows scheduled tasks

- `docs/llm-auto-heal-cron.md`
  - Usage and verification guide

## Quick start

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tasks\llm-auto-heal\scripts\setup-llm-auto-heal-cron.ps1" -DisableWindowsTask
```
