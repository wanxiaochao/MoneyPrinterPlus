#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "请先运行 ./setup-macos.sh 安装独立环境。"
  exit 1
fi
export PATH="$ROOT/.local-bin:$PATH"
PORT="${MONEYPRINTER_PORT:-8501}"
echo "MoneyPrinterPlus：http://127.0.0.1:$PORT/"
echo "停止服务：按 Ctrl+C。"
if [[ "${MONEYPRINTER_OPEN_BROWSER:-1}" == "1" ]] && command -v open >/dev/null 2>&1; then
  (sleep 2; open "http://127.0.0.1:$PORT/") >/dev/null 2>&1 &
fi
exec "$PY" -m streamlit run gui.py --server.address 127.0.0.1 --server.port "$PORT" \
  --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false
