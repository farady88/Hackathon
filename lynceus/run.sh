#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 lynceus.py status
exec python3 lynceus.py serve --port "${PORT:-8000}"
