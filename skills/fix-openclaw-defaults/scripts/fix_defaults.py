#!/usr/bin/env python3
"""
Fix OpenClaw's default context window and max tokens values.

This script patches the OpenClaw source files to change the default values
used when configuring custom models via 'openclaw configure'.

Default changes:
- DEFAULT_CONTEXT_WINDOW: 4096 → 200000
- DEFAULT_MAX_TOKENS: 4096 → 200000
"""

import os
import sys
import glob
from pathlib import Path


def find_openclaw_dist():
    """Find the OpenClaw dist directory."""
    # Try common locations
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            dist_path = Path(appdata) / 'npm' / 'node_modules' / 'openclaw' / 'dist'
            if dist_path.exists():
                return dist_path
    
    # Try npm global prefix
    try:
        import subprocess
        result = subprocess.run(['npm', 'prefix', '-g'], capture_output=True, text=True)
        if result.returncode == 0:
            npm_prefix = result.stdout.strip()
            dist_path = Path(npm_prefix) / 'node_modules' / 'openclaw' / 'dist'
            if dist_path.exists():
                return dist_path
    except:
        pass
    
    return None


def patch_file(file_path, old_context, new_context, old_max, new_max):
    """Patch a single file with new default values."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace DEFAULT_CONTEXT_WINDOW
        content = content.replace(
            f'const DEFAULT_CONTEXT_WINDOW = {old_context};',
            f'const DEFAULT_CONTEXT_WINDOW = {new_context};'
        )
        
        # Replace DEFAULT_MAX_TOKENS
        content = content.replace(
            f'const DEFAULT_MAX_TOKENS = {old_max};',
            f'const DEFAULT_MAX_TOKENS = {new_max};'
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error patching {file_path}: {e}", file=sys.stderr)
        return False


def main():
    # Configuration
    OLD_CONTEXT = 4096
    NEW_CONTEXT = '2e5'  # 200000
    OLD_MAX = 4096
    NEW_MAX = '2e5'  # 200000
    
    print("OpenClaw Default Values Patcher")
    print("=" * 50)
    print(f"Changing defaults:")
    print(f"  DEFAULT_CONTEXT_WINDOW: {OLD_CONTEXT} → {NEW_CONTEXT}")
    print(f"  DEFAULT_MAX_TOKENS: {OLD_MAX} → {NEW_MAX}")
    print()
    
    # Find OpenClaw dist directory
    dist_path = find_openclaw_dist()
    if not dist_path:
        print("ERROR: Could not find OpenClaw dist directory", file=sys.stderr)
        print("Please ensure OpenClaw is installed globally via npm", file=sys.stderr)
        return 1
    
    print(f"Found OpenClaw dist: {dist_path}")
    print()
    
    # Files to patch
    target_files = [
        'onboard-custom-*.js',
        'auth-profiles-*.js'
    ]
    
    patched_count = 0
    
    for pattern in target_files:
        files = glob.glob(str(dist_path / pattern))
        for file_path in files:
            print(f"Patching: {Path(file_path).name}...", end=' ')
            if patch_file(file_path, OLD_CONTEXT, NEW_CONTEXT, OLD_MAX, NEW_MAX):
                print("✓")
                patched_count += 1
            else:
                print("(no changes)")
    
    print()
    print(f"Patched {patched_count} file(s)")
    print()
    print("Done! Restart OpenClaw gateway for changes to take effect:")
    print("  openclaw gateway restart")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
