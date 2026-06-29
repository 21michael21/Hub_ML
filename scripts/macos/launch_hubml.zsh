#!/bin/zsh
set -euo pipefail

export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"

APP_ROOT="${HUBML_APP_ROOT:-__HUBML_PROJECT_ROOT__}"
APP_NAME="Hub_ML"
HOST="127.0.0.1"
PORT_START="${HUBML_PORT:-8501}"
LOG_DIR="$HOME/Library/Logs/Hub_ML"
LOG_FILE="$LOG_DIR/Hub_ML.log"

mkdir -p "$LOG_DIR"
cd "$APP_ROOT"

log() {
  print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

fail() {
  log "ERROR: $*"
  osascript -e "display alert \"$APP_NAME\" message \"$*\" as critical" >/dev/null 2>&1 || true
  exit 1
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  fail "python3 не найден. Установи Python 3.11+ и запусти приложение снова."
}

ensure_venv() {
  local python_bin="$1"
  if [ ! -d ".venv" ]; then
    log "creating .venv"
    "$python_bin" -m venv .venv >> "$LOG_FILE" 2>&1
  fi

  if [ ! -x ".venv/bin/python" ]; then
    fail "Виртуальное окружение .venv повреждено: .venv/bin/python не найден."
  fi
}

requirements_hash() {
  if [ -f "requirements.txt" ]; then
    shasum -a 256 requirements.txt | awk '{print $1}'
  else
    print -r -- "missing"
  fi
}

ensure_dependencies() {
  local stamp=".venv/.hubml_requirements_sha256"
  local current_hash
  current_hash="$(requirements_hash)"

  if [ ! -f "$stamp" ] || [ "$(cat "$stamp" 2>/dev/null || true)" != "$current_hash" ]; then
    log "installing dependencies"
    .venv/bin/python -m pip install --upgrade pip >> "$LOG_FILE" 2>&1
    .venv/bin/python -m pip install -r requirements.txt >> "$LOG_FILE" 2>&1
    print -r -- "$current_hash" > "$stamp"
  fi

  .venv/bin/python - <<'PY' >> "$LOG_FILE" 2>&1 || {
import streamlit
import pandas
import jupyter_client
PY
    log "dependency import check failed; reinstalling requirements"
    .venv/bin/python -m pip install -r requirements.txt >> "$LOG_FILE" 2>&1
  }
}

choose_port() {
  local port="$PORT_START"
  while [ "$port" -le 8510 ]; do
    if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      print -r -- "$port"
      return
    fi
    port=$((port + 1))
  done
  fail "Порты 8501-8510 заняты. Освободи один порт и запусти приложение снова."
}

wait_for_server() {
  local url="$1"
  .venv/bin/python - "$url" <<'PY'
import sys
import time
import urllib.request

url = sys.argv[1]
deadline = time.time() + 45
while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            if response.status < 500:
                raise SystemExit(0)
    except Exception:
        time.sleep(0.5)
raise SystemExit(1)
PY
}

main() {
  log "starting $APP_NAME from $APP_ROOT"
  local python_bin
  python_bin="$(find_python)"
  ensure_venv "$python_bin"
  ensure_dependencies

  local vault_default
  vault_default="$(cd "$APP_ROOT/.." && pwd)/obsidian_vkat"
  if [ -z "${VAULT_PATH:-}" ] && [ -d "$vault_default" ]; then
    export VAULT_PATH="$vault_default"
  fi

  local port
  port="$(choose_port)"
  local url="http://$HOST:$port"

  log "launching Streamlit on $url"
  .venv/bin/python -m streamlit run app.py \
    --server.address "$HOST" \
    --server.port "$port" \
    --server.headless true \
    >> "$LOG_FILE" 2>&1 &

  local server_pid="$!"
  if wait_for_server "$url"; then
    open "$url"
  else
    kill "$server_pid" >/dev/null 2>&1 || true
    fail "Streamlit не стартовал за 45 секунд. Лог: $LOG_FILE"
  fi

  wait "$server_pid"
}

main "$@"
