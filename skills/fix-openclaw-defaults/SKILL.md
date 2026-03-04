---
name: fix-openclaw-defaults
description: "Fix OpenClaw's default context window and max tokens values when configuring custom models. Use when: (1) OpenClaw configure sets context window or max tokens to 4096 by default, (2) custom models fail due to low token limits, (3) user wants to change the default values used by 'openclaw configure' for new custom model configurations. This patches the OpenClaw source files to use 200000 for both context window and max tokens instead of 4096."
---

# Fix OpenClaw Defaults

This skill fixes OpenClaw's hardcoded default values for context window and max tokens when configuring custom models via `openclaw configure`.

## Problem

When you run `openclaw configure` to add a custom model, OpenClaw hardcodes these defaults in the source:

- `DEFAULT_CONTEXT_WINDOW = 4096`
- `DEFAULT_MAX_TOKENS = 4096`

This causes issues with modern models that support much larger context windows and output limits.

## Solution

Run the fix script to patch OpenClaw's source files:

```bash
python scripts/fix_defaults.py
```

The script will:

1. Locate your OpenClaw installation (typically in `%APPDATA%\npm\node_modules\openclaw\dist`)
2. Patch these files:
   - `onboard-custom-*.js` (2 files) - Used when configuring custom models
   - `auth-profiles-*.js` (1 file) - Used for Bedrock discovery
3. Change defaults to:
   - `DEFAULT_CONTEXT_WINDOW = 2e5` (200,000)
   - `DEFAULT_MAX_TOKENS = 2e5` (200,000)

After running the script, restart the OpenClaw gateway:

```bash
openclaw gateway restart
```

## When to Use

- After installing or updating OpenClaw
- When `openclaw configure` creates models with 4096 limits
- When custom models fail with "max tokens exceeded" errors
- Before configuring new custom model providers

## Notes

- This patches the installed OpenClaw source files
- Changes persist until OpenClaw is updated/reinstalled
- Existing model configurations in `openclaw.json` are not affected
- You can manually edit `openclaw.json` to fix existing models
