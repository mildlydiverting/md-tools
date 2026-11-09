#!/bin/bash

# Path to cwebp — adjust if yours differs (run `which cwebp` to check)
CWEBP="/opt/homebrew/bin/cwebp"

convert_file() {
    local input="$1"
    local output="${input%.png}.webp"
    "$CWEBP" -lossless -quiet "$input" -o "$output"
    echo "Converted: $input → $output"
}

for item in "$@"; do
    if [ -d "$item" ]; then
        # Folder: recurse
        while IFS= read -r -d '' file; do
            convert_file "$file"
        done < <(find "$item" -type f -iname "*.png" -print0)
    elif [ -f "$item" ] && [[ "${item,,}" == *.png ]]; then
        # Single file
        convert_file "$item"
    fi
done