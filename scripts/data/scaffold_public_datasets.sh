#!/usr/bin/env bash
set -euo pipefail
BASE="datasets/public"
DATASETS=("xview" "dota" "visdrone" "semantic-drone" "ddos")
mkdir -p "$BASE"
for d in "${DATASETS[@]}"; do
  mkdir -p "$BASE/$d/raw" "$BASE/$d/processed"
  if [ ! -f "$BASE/$d/README.md" ]; then
    cat > "$BASE/$d/README.md" <<EOF
# ${d^^} dataset (scaffold)

- Put original archives/files in \`raw/\`
- Put converted/standardized files in \`processed/\`
- Keep large data **out of Git** (tracked by .gitignore)
- Add LICENSE/attribution notes in this file when downloaded.

EOF
  fi
done
echo "Scaffold created under $BASE/"
