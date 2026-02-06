#!/bin/bash
# BuildStream + Buildbarn PoC Helper Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip wheel
    pip install BuildStream buildstream-plugins
else
    source "$VENV_DIR/bin/activate"
fi

cd "$SCRIPT_DIR"

case "${1:-help}" in
    build)
        echo "Building hello.bst..."
        bst build hello.bst
        ;;
    show)
        echo "Showing pipeline status..."
        bst show hello.bst
        ;;
    checkout)
        OUTPUT_DIR="${2:-/tmp/buildstream-output}"
        echo "Checking out to $OUTPUT_DIR..."
        rm -rf "$OUTPUT_DIR"
        bst artifact checkout hello.bst --directory "$OUTPUT_DIR"
        echo "Output at: $OUTPUT_DIR/usr/bin/hello"
        ;;
    run)
        OUTPUT_DIR="/tmp/buildstream-output"
        if [ ! -f "$OUTPUT_DIR/usr/bin/hello" ]; then
            echo "Build artifact not found, building first..."
            bst build hello.bst
            rm -rf "$OUTPUT_DIR"
            bst artifact checkout hello.bst --directory "$OUTPUT_DIR"
        fi
        echo "Running in Alpine container..."
        docker run --rm -v "$OUTPUT_DIR/usr/bin/hello:/hello" alpine:3.19 \
            sh -c "apk add --no-cache libstdc++ >/dev/null 2>&1 && /hello"
        ;;
    clean)
        echo "Cleaning build cache..."
        rm -rf ~/.cache/buildstream/artifacts/refs/buildstream-buildbarn-poc
        rm -rf ~/.cache/buildstream/build/buildstream-buildbarn-poc
        ;;
    shell)
        echo "Opening shell in build sandbox for hello.bst..."
        bst shell hello.bst
        ;;
    help|*)
        echo "BuildStream PoC Helper"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  build      Build hello.bst element"
        echo "  show       Show pipeline status"
        echo "  checkout   Checkout artifact to /tmp/buildstream-output (or specify path)"
        echo "  run        Build, checkout, and run in Alpine container"
        echo "  clean      Clean build cache"
        echo "  shell      Open interactive shell in build sandbox"
        echo "  help       Show this help"
        ;;
esac
