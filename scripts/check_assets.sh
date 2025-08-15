#!/usr/bin/env bash
set -e
echo "Checking key files..."
req=(
  schema/event.schema.json
  assets/dialogue/en/characters.json
  assets/dialogue/en/core/phase0_intro.json
  assets/events/main/000_story_start.json
  platinum/cli.py
  platinum/events/engine.py
  platinum/ui/dialogue_manager.py
)
missing=0
for f in "${req[@]}"; do
  if [ -f "$f" ]; then
    echo " OK  $f"
  else
    echo " MISSING $f"; missing=1
  fi
done
exit $missing