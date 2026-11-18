#!/bin/bash
# Prepend creation date (YYYY-MM-DD) to each file passed as an argument.
# Use in Automator: "Run Shell Script" action, "Pass input: as arguments"

for f in "$@"; do
    # Get the file's creation date via GetFileInfo
    created=$(GetFileInfo -d "$f" | awk '{print $1}')

    # created is in MM/DD/YYYY format — reformat to YYYY-MM-DD
    month=$(echo "$created" | cut -d'/' -f1)
    day=$(echo "$created"   | cut -d'/' -f2)
    year=$(echo "$created"  | cut -d'/' -f3)
    date_prefix="${year}-${month}-${day}"

    dir=$(dirname "$f")
    base=$(basename "$f")

    # Skip if already prefixed with a date in this format
    if [[ "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}- ]]; then
        echo "Skipping (already prefixed): $base"
        continue
    fi

    new_path="${dir}/${date_prefix}-${base}"
    mv "$f" "$new_path"
    echo "Renamed: $base → ${date_prefix}-${base}"
done
