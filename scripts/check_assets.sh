#!/usr/bin/env bash
set -euo pipefail

echo "Checking Pokemon Platinum assets..."

# Check required directories
echo "Checking directories..."
required_dirs=(
    "schema"
    "assets/dialogue/en/core"
    "assets/dialogue/en/variants"
    "assets/dialogue/en/meta"
    "assets/events/main"
    "assets/events/galactic"
    "assets/battle_configs/rival"
    "src/platinum"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "ERROR: Missing directory: $dir"
        exit 1
    fi
done
echo "✓ All required directories exist"

# Check required files
echo "Checking required files..."
required_files=(
    "schema/event.schema.json"
    "assets/dialogue/en/characters.json"
    "assets/dialogue/en/core/phase0_intro.json"
    "assets/dialogue/en/core/phase1_early_routes.json"
    "assets/dialogue/en/core/phase2_windworks.json"
    "assets/dialogue/en/variants/selector_config.json"
    "assets/dialogue/en/meta/provenance.json"
    "assets/events/main/000_story_start.json"
    "assets/events/main/010_rival_initial_visit.json"
    "assets/events/main/020_route201_attempt.json"
    "assets/events/main/030_starter_selection.json"
    "assets/events/main/040_running_shoes.json"
    "assets/events/galactic/120_windworks_commander.json"
    "assets/battle_configs/rival/rival_1.json"
    "main.py"
    "src/platinum/__init__.py"
    "src/platinum/__main__.py"
    "src/platinum/cli.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Missing file: $file"
        exit 1
    fi
done
echo "✓ All required files exist"

# Check JSON validity
echo "Checking JSON validity..."
json_files=$(find assets/ schema/ -name "*.json" -type f)

for file in $json_files; do
    if ! python -m json.tool "$file" > /dev/null 2>&1; then
        echo "ERROR: Invalid JSON in file: $file"
        exit 1
    fi
done
echo "✓ All JSON files are valid"

# Test Python module loading
echo "Testing Python module loading..."
if ! python -c "import src.platinum.cli" 2>/dev/null; then
    echo "ERROR: Cannot import platinum CLI module"
    exit 1
fi
echo "✓ Python modules load correctly"

# Test event loading (if jsonschema is available)
echo "Testing event loading..."
if python -c "import jsonschema" 2>/dev/null; then
    if ! python -c "from src.platinum.events.loader import load_events; reg = load_events(); print(f'Loaded {len(reg.all())} events')" 2>/dev/null; then
        echo "ERROR: Event loading failed"
        exit 1
    fi
    echo "✓ Event loading works correctly"
else
    echo "⚠ jsonschema not installed - skipping schema validation test"
fi

echo
echo "All asset checks passed! 🎉"
echo "The Pokemon Platinum project structure is ready."