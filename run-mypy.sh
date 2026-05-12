#!/usr/bin/env sh

set -o errexit

# Change directory to the project root directory.
cd "$(dirname "$0")"

# Use venv's poetry or mypy directly
if [ -f "venv/bin/mypy" ]; then
    venv/bin/mypy --strict .
elif [ -f "venv/bin/poetry" ]; then
    venv/bin/poetry run mypy --strict .
else
    poetry run mypy --strict .
fi
