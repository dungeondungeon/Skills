#!/usr/bin/env bash
# Link every skills/* folder into ~/.claude/skills (macOS / Linux).
set -euo pipefail
repo="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.claude/skills
for d in "$repo"/skills/*/; do
  name="$(basename "$d")"; dest=~/.claude/skills/"$name"
  if [ -e "$dest" ]; then echo "skip  $name: $dest already exists"; else ln -s "${d%/}" "$dest"; echo "link  $name"; fi
done
