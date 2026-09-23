#!/usr/bin/env bash
# Sobe o dig.D Vídeo. Por padrão escuta só nesta máquina (127.0.0.1:8742).
#
#   scripts/rodar.sh
#   VIDEOS_HOST=0.0.0.0 VIDEOS_TOKEN=... scripts/rodar.sh   # abrir pra rede: SÓ com token
set -euo pipefail
PACOTE="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PACOTE/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

# Host, porta e token saem do mesmo lugar que a API lê (ambiente ou .env).
read -r HOST PORTA TEM_TOKEN < <("$PY" -c '
import os, sys
sys.path.insert(0, sys.argv[1])
import config
print(os.environ.get("VIDEOS_HOST") or "127.0.0.1", os.environ.get("VIDEOS_PORTA") or "8742", 1 if config.TOKEN else 0)
' "$PACOTE/api")

if [ "$HOST" != "127.0.0.1" ] && [ "$HOST" != "localhost" ] && [ "$TEM_TOKEN" != 1 ]; then
  echo "Recusei subir em $HOST sem VIDEOS_TOKEN: qualquer um na rede veria e apagaria os vídeos." >&2
  exit 1
fi

echo "dig.D Vídeo em http://$HOST:$PORTA/editor"
exec "$PY" -m uvicorn servidor:app --app-dir "$PACOTE/api" --host "$HOST" --port "$PORTA"
