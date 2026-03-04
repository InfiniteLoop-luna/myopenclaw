# myopenclaw

Personal OpenClaw automation scripts, organized by **task** for reuse.

## Repository layout

```text
myopenclaw/
  tasks/
    llm-auto-heal/
      scripts/
      docs/
      README.md
    _template/
      README.md
```

## Current tasks

- `tasks/llm-auto-heal` — LLM model auto-heal + cron setup

## Why task-first structure

- Easy to copy one task directory to another machine
- Better scalability when you add many reusable automations
- Clear ownership: each task has its own scripts/docs/readme
