# Tasks Index

Central registry of reusable automation tasks.

| Task | Purpose | Platform | Entrypoint | Status |
|---|---|---|---|---|
| `llm-auto-heal` | Detect LLM errors, switch to healthy model, restart gateway, and keep cron schedule healthy | Windows / OpenClaw | `tasks/llm-auto-heal/scripts/setup-llm-auto-heal-cron.ps1` | Active |

---

## Add a new task

1. Copy `tasks/_template` to `tasks/<your-task-name>`
2. Fill in `README.md` and optional `task.meta.json`
3. Add one row to this index table
4. Commit + push
