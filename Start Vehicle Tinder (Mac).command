#!/bin/bash
# Double-click this file to start Vehicle Tinder (macOS / Linux).
# Keep this file inside the "Vehicle tinder" folder.

set -e
cd "$(dirname "$0")"

pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  return 1
}

PYTHON_BIN="$(pick_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo ""
  echo "Python 3 was not found."
  echo "Install it from https://www.python.org/downloads/ then try again."
  echo ""
  read -r -p "Press Enter to close…"
  exit 1
fi

echo "Starting Vehicle Tinder with: $PYTHON_BIN"
echo "A browser window should open shortly."
echo "Leave this window open while you label. Press Ctrl+C to stop."
echo ""

"$PYTHON_BIN" app.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo ""
  echo "The app exited with an error (code $EXIT_CODE)."
  read -r -p "Press Enter to close…"
fi

exit $EXIT_CODE
