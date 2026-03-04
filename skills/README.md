# skills

This directory stores reusable OpenClaw skills.

- Source of truth (current workflow): local workspace `C:\Users\lijing\.openclaw\workspace\skills`
- Repository mirror path: `skills/`

See `skills/index.md` for a quick list.

## Publish workflow

- Sync only: `tools/sync-skills.ps1`
- Sync + commit + push: `tools/publish-skills.ps1`

Examples:

```powershell
# Preview changes only
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -DryRun

# Publish + push + auto-tag
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\publish-skills.ps1" -TagAfterPush
```
