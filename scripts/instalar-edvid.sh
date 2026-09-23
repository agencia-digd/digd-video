#!/usr/bin/env bash
# Instala o edvid (github.com/fillrochaa/edvid, MIT, © Creator Factory) em
# vendor/edvid, no commit com que o dig.D Vídeo foi testado, e aplica em cima o
# que o dig.D Vídeo precisa dele (pasta edvid-extras/).
#
#   scripts/instalar-edvid.sh                 # tudo
#   scripts/instalar-edvid.sh --sem-python    # pula o venv com WhisperX (~2 GB)
#   scripts/instalar-edvid.sh --sem-node      # pula o npm install do Remotion
#   scripts/instalar-edvid.sh --sem-trilhas   # não baixa as trilhas da Mixkit
#
# Pode rodar de novo: o que já está feito é pulado.
set -euo pipefail

PACOTE="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${VIDEOS_EDVID:-$PACOTE/vendor/edvid}"
REPO="https://github.com/fillrochaa/edvid"
# Commit testado (main de 15/08/2026). Trocar de commit = testar o patch de novo.
COMMIT="d8e6389db02e8de0b46ee680105c09d4250d4703"
EXTRAS="$PACOTE/edvid-extras"

SEM_PYTHON=0; SEM_NODE=0; SEM_TRILHAS=0
for a in "$@"; do
  case "$a" in
    --sem-python) SEM_PYTHON=1 ;;
    --sem-node) SEM_NODE=1 ;;
    --sem-trilhas) SEM_TRILHAS=1 ;;
    *) echo "opção desconhecida: $a" >&2; exit 2 ;;
  esac
done

falta=()
for bin in git ffmpeg ffprobe python3; do
  command -v "$bin" >/dev/null || falta+=("$bin")
done
if [ "$SEM_NODE" = 0 ]; then
  command -v node >/dev/null || falta+=("node (18+)")
  command -v npm >/dev/null || falta+=("npm")
fi
if [ "${#falta[@]}" -gt 0 ]; then
  echo "Falta instalar: ${falta[*]}" >&2
  exit 1
fi
if [ "$SEM_NODE" = 0 ]; then
  maior="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$maior" -lt 18 ]; then
    echo "O Remotion pede Node 18 ou mais novo; este é o $(node -v)." >&2
    exit 1
  fi
fi

echo "[1/5] edvid em $DESTINO"
if [ ! -d "$DESTINO/.git" ]; then
  mkdir -p "$(dirname "$DESTINO")"
  git clone --quiet "$REPO" "$DESTINO"
fi
git -C "$DESTINO" -c advice.detachedHead=false checkout --quiet "$COMMIT" 2>/dev/null || {
  echo "Não consegui pôr o edvid no commit $COMMIT." >&2
  echo "Se você mexeu em $DESTINO, guarde suas mudanças ou apague a pasta e rode de novo." >&2
  exit 1
}

echo "[2/5] patch do dig.D Vídeo (card de fechamento, enquadramento da tela dividida, correção do render)"
if git -C "$DESTINO" apply --reverse --check "$EXTRAS/patches/digd-video.patch" 2>/dev/null; then
  echo "      já aplicado"
else
  git -C "$DESTINO" apply "$EXTRAS/patches/digd-video.patch"
fi
cp "$EXTRAS/helpers/encode_social.py" "$EXTRAS/helpers/pick_bed.py" "$DESTINO/helpers/"

echo "[3/5] trilhas"
if [ "$SEM_TRILHAS" = 1 ]; then
  echo "      puladas (--sem-trilhas): os vídeos saem sem trilha"
else
  mkdir -p "$DESTINO/assets/music/beds"
  cp "$EXTRAS/music/catalog.json" "$DESTINO/assets/music/catalog.json"
  # As faixas vêm da própria Mixkit, na sua máquina: a licença deles permite
  # usar em vídeo, mas não redistribuir o MP3 num pacote. Por isso não vêm junto.
  python3 - "$DESTINO/assets/music" <<'PY'
import json, sys, urllib.request
from pathlib import Path
base = Path(sys.argv[1])
cat = json.loads((base / "catalog.json").read_text(encoding="utf-8"))
for b in cat["beds"]:
    dest = base / b["file"]
    if dest.exists() and dest.stat().st_size > 0:
        print(f"      {b['id']:6} já baixada"); continue
    try:
        req = urllib.request.Request(b["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())
        print(f"      {b['id']:6} {b['title']} — {b['artist']}")
    except Exception as e:  # noqa: BLE001 — trilha não bloqueia a instalação
        print(f"      {b['id']:6} NÃO baixou ({e}); esse clima sai sem trilha")
PY
fi

echo "[4/5] Python do edvid (WhisperX)"
if [ "$SEM_PYTHON" = 1 ]; then
  echo "      pulado (--sem-python). Sem WhisperX nenhum vídeo passa da primeira etapa."
elif [ -x "$DESTINO/.venv/bin/python" ] && "$DESTINO/.venv/bin/python" -c "import whisperx" 2>/dev/null; then
  echo "      já instalado"
elif command -v uv >/dev/null; then
  uv sync --directory "$DESTINO"
else
  # Sem uv: venv comum. O edvid pede Python 3.10 a 3.13.
  python3 -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' || {
    echo "O edvid pede Python 3.10 a 3.13 e este é o $(python3 -V). Instale o uv (docs.astral.sh/uv) e rode de novo." >&2
    exit 1
  }
  python3 -m venv "$DESTINO/.venv"
  "$DESTINO/.venv/bin/pip" install --quiet --upgrade pip
  "$DESTINO/.venv/bin/pip" install --quiet -e "$DESTINO"
fi

echo "[5/5] Remotion (template de legenda)"
if [ "$SEM_NODE" = 1 ]; then
  echo "      pulado (--sem-node). Sem isso não há legenda nem estilo."
else
  if [ -d "$DESTINO/assets/shortform/node_modules/remotion" ]; then
    echo "      pacotes já instalados"
  else
    (cd "$DESTINO/assets/shortform" && npm install --no-audit --no-fund)
  fi
  # O Chrome headless que o Remotion usa pra renderizar. Sem isto ele é baixado
  # DENTRO da cópia de trabalho de cada render — que é apagada no fim —, e cada
  # vídeo baixaria o navegador de novo. Instalado no template, vai junto na cópia.
  (cd "$DESTINO/assets/shortform" && npx --no-install remotion browser ensure)
fi

echo
echo "Pronto. edvid em $DESTINO (commit ${COMMIT:0:7} + patch do dig.D Vídeo)."
