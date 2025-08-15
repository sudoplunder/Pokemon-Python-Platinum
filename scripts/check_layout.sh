#!/usr/bin/env bash
set -e
paths=(
  schema/event.schema.json
  assets/dialogue/en/core/phase0_intro.json
  assets/events/main/030_starter_selection.json
  assets/battle_configs/rival/rival_1.json
  src/platinum/cli.py
  src/platinum/ui/dialogue_manager.py
  src/platinum/events/loader.py
)
echo "Verifying expected files..."
missing=0
for p in "${paths[@]}"; do
  if [ -f "$p" ]; then
    echo " OK  $p"
  else
    echo " MISSING $p"; missing=1
  fi
done
exit $missing