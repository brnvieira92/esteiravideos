#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
