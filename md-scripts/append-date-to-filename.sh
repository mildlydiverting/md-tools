#!/bin/bash
# Append creation date (YYYY-MM-DD) to each file passed as an argument.
# e.g. orders-4.csv → orders-4-2026-05-01.csv
# Use in Automator: "Run Shell Script" action, "Pass input: as arguments"

for f in "$@"; do
    # Get the file's creation date via GetFileInfo
    created=$(GetFileInfo -d "$f" | awk '{print $1}')

    # created is in MM/DD/YYYY format — reformat to YYYY-MM-DD
    month=$(echo "$created" | cut -d'/' -f1)
    day=$(echo "$created"   | cut -d'/' -f2)
    year=$(echo "$created"  | cut -d'/' -f3)
    date_suffix="${year}-${month}-${day}"

    dir=$(dirname "$f")
    base=$(basename "$f")

    # Split into name and extension
    name="${base%.*}"
    ext="${base##*.}"

    # If there's no extension, ext equals base — handle gracefully
    if [ "$ext" = "$base" ]; then
        ext=""
        new_name="${name}-${date_suffix}"
    else
        new_name="${name}-${date_suffix}.${ext}"
    fi

    # Skip if already ends with a date in this format (before the extension)
    if [[ "$name" =~ -[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "Skipping (already suffixed): $base"
        continue
    fi

    new_path="${dir}/${new_name}"
    mv "$f" "$new_path"
    echo "Renamed: $base → ${new_name}"
done
