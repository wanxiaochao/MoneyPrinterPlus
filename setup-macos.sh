#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if ! command -v uv >/dev/null 2>&1; then
  echo "请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  uv venv --python 3.11 "$ROOT/.venv"
fi
uv pip install --python "$ROOT/.venv/bin/python" -r requirements-macos.txt
mkdir -p work final resource
export PATH="$ROOT/.local-bin:$PATH"
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "Python依赖已安装。还需安装FFmpeg（例如 brew install ffmpeg）。"
  exit 1
fi
echo "环境就绪，双击 start-macos.command 启动。"
