#!/usr/bin/env bash
# Readiness Assistant Warmup Script
set -e

echo "Starting Readiness Assistant Warmup..."
python3 "$(dirname "$0")/warmup.py" || python "$(dirname "$0")/warmup.py"
