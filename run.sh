#!/bin/bash

# Get the absolute path of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOOL=$1 

if [ -z "$TOOL" ]; then
    echo "Usage: $0 <tool>"
    exit 1
fi

TOOL_DIR=$DIR/tools/$TOOL

if [ ! -d "$TOOL_DIR" ]; then
    echo "Error: Tool directory $TOOL_DIR does not exist"
    exit 1
fi

if [ ! -e "$TOOL_DIR/.venv" ]; then
    echo "Creating virtual environment for $TOOL..."
    uv venv $TOOL_DIR/.venv
    source $TOOL_DIR/.venv/bin/activate

    if [ -f "$TOOL_DIR/pyproject.toml" ]; then
        echo "Installing dependencies for $TOOL..."
        uv pip install -e "$TOOL_DIR"
    fi
else
    source $TOOL_DIR/.venv/bin/activate
fi

python "$TOOL_DIR/main.py" "${@:2}"
EXIT_CODE=$?

deactivate

exit $EXIT_CODE