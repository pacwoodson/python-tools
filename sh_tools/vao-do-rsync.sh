#!/bin/bash

# Check if source argument is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <source>"
    echo "Example: $0 /path/to/source"
    exit 1
fi

# Store source from first argument
SOURCE="$1"
# Set fixed destination
DEST="opac-vao:opac-vao"

# Check if source exists
if [ ! -e "$SOURCE" ]; then
    echo "Error: Source '$SOURCE' does not exist"
    exit 1
fi

# Perform rclone copy
rclone copy \
    --progress \
    --s3-chunk-size 20M \
    --s3-upload-concurrency 4 \
    --transfers 2 \
    --retries 3 \
    --low-level-retries 10 \
    --tpslimit 10 \
    "$SOURCE" "$DEST"

# Check rclone exit status
if [ $? -eq 0 ]; then
    echo "Copy completed successfully"
else
    echo "Copy failed with error code $?"
    exit 1
fi
