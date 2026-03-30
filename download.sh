#!/bin/bash

# Locate repo/app folder (supports running from inside or next to it)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
APP_DIR="$SCRIPT_DIR"

# If the script sits beside a repo folder, try known folder names
if [ ! -f "$APP_DIR/src/main.py" ] && [ -f "$SCRIPT_DIR/TikTokAccountDownloader/src/main.py" ]; then
    APP_DIR="$SCRIPT_DIR/TikTokAccountDownloader"
fi
if [ ! -f "$APP_DIR/src/main.py" ] && [ -f "$SCRIPT_DIR/TikTokScanner-main/src/main.py" ]; then
    APP_DIR="$SCRIPT_DIR/TikTokScanner-main"
fi

# Verify entry point exists
if [ ! -f "$APP_DIR/src/main.py" ]; then
    echo "ERROR: Could not find src/main.py."
    echo "Put this shell script inside the project folder, or next to a valid repo folder."
    read -n 1 -s -r -p "Press any key to continue..."
    echo
    exit 1
fi

# Always use system Python (fallback to python3 if available)
if command -v python3 &> /dev/null; then
    PYTHON_EXE="python3"
else
    PYTHON_EXE="python"
fi

# Load optional .env file (supports MONGO_URI, etc.)
if [ -f "$APP_DIR/.env" ]; then
    # Parse .env handling comments and stripping quotes
    while IFS='=' read -r key value; do
        if [[ ! -z "$key" && "$key" != \#* ]]; then
            # Strip quotes
            value="${value%\"}"
            value="${value#\"}"
            export "$key=$value"
        fi
    done < "$APP_DIR/.env"
fi

usage() {
    echo ""
    echo "Usage: $0 [URL|@username] [--concurrent N] [--headless] [--no-headless] [--force-full-scan] [--no-full-scan] [--cookies-file PATH] [--mongo-uri URI]"
    echo ""
    echo "If no arguments are provided, this script will prompt for values."
    echo "Defaults: --concurrent 3, headless mode, early-stop scan enabled."
    echo ""
    echo "This script will load an optional .env file from the repo root (if present)."
    echo "You can set MONGO_URI via .env or environment variable to enable database tracking."
    echo ""
    exit 0
}

# Parse CLI args
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

ARG_URL=""
ARG_CONCURRENT=""
ARG_HEADLESS=""
ARG_FULLSCAN=""
ARG_COOKIES_FILE=""
ARG_MONGO_URI=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --headless)
            ARG_HEADLESS="1"
            shift
            ;;
        --no-headless)
            ARG_HEADLESS="0"
            shift
            ;;
        --force-full-scan)
            ARG_FULLSCAN="1"
            shift
            ;;
        --no-full-scan)
            ARG_FULLSCAN="0"
            shift
            ;;
        --concurrent)
            ARG_CONCURRENT="$2"
            shift 2
            ;;
        --cookies-file)
            ARG_COOKIES_FILE="$2"
            shift 2
            ;;
        --mongo-uri)
            ARG_MONGO_URI="$2"
            shift 2
            ;;
        *)
            if [ -z "$ARG_URL" ]; then
                ARG_URL="$1"
            else
                echo "WARNING: Ignoring extra argument: $1"
            fi
            shift
            ;;
    esac
done

start_run() {
    # Prompt for missing values (only URL is required)
    while [ -z "$ARG_URL" ]; do
        read -p "Enter TikTok Profile URL (or @username): " ARG_URL
    done

    # Default settings (no prompting)
    if [ -z "$ARG_CONCURRENT" ]; then ARG_CONCURRENT="3"; fi
    if [ -z "$ARG_HEADLESS" ]; then ARG_HEADLESS="1"; fi

    # Ask user if full scan should be enabled when not explicitly provided
    if [ -z "$ARG_FULLSCAN" ]; then
        echo ""
        echo "Full scan checks the whole profile and can take longer."
        while true; do
            read -p "Enable full scan? [Y/N]: " yn
            case $yn in
                [Yy]* ) ARG_FULLSCAN="1"; break;;
                [Nn]* ) ARG_FULLSCAN="0"; break;;
                * ) echo "Please answer Y or N.";;
            esac
        done
    fi

    # Validate concurrent (must be positive integer)
    if ! [[ "$ARG_CONCURRENT" =~ ^[0-9]+$ ]]; then
        ARG_CONCURRENT="3"
    fi
    if [ "$ARG_CONCURRENT" -lt 1 ]; then
        ARG_CONCURRENT="1"
    fi

    # Default cookies path
    if [ -z "$ARG_COOKIES_FILE" ] && [ -f "$APP_DIR/src/cookies.txt" ]; then
        ARG_COOKIES_FILE="$APP_DIR/src/cookies.txt"
    fi

    # Default mongo uri from environment (optional)
    if [ -z "$ARG_MONGO_URI" ] && [ -n "$MONGO_URI" ]; then
        ARG_MONGO_URI="$MONGO_URI"
    fi

    # Build flags
    HEADLESS_FLAG=""
    if [ "$ARG_HEADLESS" = "1" ]; then HEADLESS_FLAG="--headless"; fi

    FULLSCAN_FLAG=""
    if [ "$ARG_FULLSCAN" = "1" ]; then FULLSCAN_FLAG="--force-full-scan"; fi

    # Run
    echo "Running from: $APP_DIR"
    pushd "$APP_DIR" > /dev/null

    # Build the command arguments array
    CMD_ARGS=("$ARG_URL")
    if [ -n "$HEADLESS_FLAG" ]; then CMD_ARGS+=("$HEADLESS_FLAG"); fi
    if [ -n "$FULLSCAN_FLAG" ]; then CMD_ARGS+=("$FULLSCAN_FLAG"); fi
    CMD_ARGS+=("-c" "$ARG_CONCURRENT")
    if [ -n "$ARG_COOKIES_FILE" ]; then CMD_ARGS+=("--cookies-file" "$ARG_COOKIES_FILE"); fi
    if [ -n "$ARG_MONGO_URI" ]; then CMD_ARGS+=("--mongo-uri" "$ARG_MONGO_URI"); fi

    "$PYTHON_EXE" src/main.py "${CMD_ARGS[@]}"

    popd > /dev/null

    echo ""
    while true; do
        read -p "Press [S] to scan another user, or [E] to exit: " se
        case $se in
            [Ee]* ) exit 0;;
            [Ss]* ) 
                ARG_URL=""
                ARG_FULLSCAN=""
                start_run
                return
                ;;
            * ) echo "Please answer S or E.";;
        esac
    done
}

start_run
