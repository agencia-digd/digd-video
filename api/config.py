"""Configuração do dig.D Vídeo — tudo o que muda de uma máquina pra outra.

Cada valor vem de variável de ambiente e tem um padrão que funciona quando se
segue o README: o edvid instalado em `vendor/edvid` pelo
`scripts/instalar-edvid.sh`, e os vídeos guardados em `dados/`, ambos dentro da
pasta do pacote.

---------------------------------------------------------------------------
POR QUE UM ARQUIVO SÓ

Os scripts da fila (processar, falas, fase2, capa…) rodam como processos
separados, chamados pelo servidor. Se cada um lesse o ambiente do seu jeito, um
caminho trocado no `.env` valeria pra metade deles e a outra metade seguiria
procurando no lugar antigo — o tipo de erro que só aparece no meio de um render.
Aqui cada caminho é resolvido uma vez, do mesmo jeito, pra todos.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent          # api/
PACOTE = AQUI.parent                            # raiz do pacote


def _carregar_env(arquivo: Path) -> None:
    """Lê o `.env` da raiz do pacote, sem sobrescrever o que já veio do ambiente.

    Sem dependência nova: é `CHAVE=valor` por linha, `#` comenta. Quem prefere
    exportar as variáveis no shell (ou num serviço do systemd) não precisa dele."""
    if not arquivo.is_file():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(chave.strip(), valor)


_carregar_env(PACOTE / ".env")


def _caminho(nome: str, padrao: Path) -> Path:
    v = os.environ.get(nome, "").strip()
    return Path(v).expanduser().resolve() if v else padrao


# Onde ficam os vídeos (um JSON de estado e os arquivos de cada um) e as
# referências de estilo das capas e das artes.
RAIZ = _caminho("VIDEOS_RAIZ", PACOTE / "dados")
REFERENCIAS = _caminho("VIDEOS_REFERENCIAS", RAIZ / "referencias")
REFERENCIAS_ARTE = REFERENCIAS / "arte"

# O edvid (fillrochaa/edvid, MIT) — motor de corte, transcrição e render.
EDVID = _caminho("VIDEOS_EDVID", PACOTE / "vendor" / "edvid")
EDVID_HELPERS = EDVID / "helpers"

# O template do Remotion que a Fase 2 copia a cada render. Precisa ter
# `node_modules` instalado (npm install) — o script de instalação faz isso.
REMOTION = _caminho("VIDEOS_REMOTION", EDVID / "assets" / "shortform")


def _python_transcricao() -> Path:
    """O Python que tem o WhisperX. O resto dos scripts roda no Python do servidor.

    A transcrição é a única parte que precisa de torch/whisperx (~2 GB). Por
    isso ela tem um Python próprio: o venv do edvid, se existir."""
    v = os.environ.get("VIDEOS_PYTHON", "").strip()
    if v:
        return Path(v).expanduser()
    for venv in (EDVID / ".venv" / "bin" / "python", EDVID / ".venv" / "Scripts" / "python.exe"):
        if venv.exists():
            return venv
    return Path(sys.executable)


PY_TRANSCRICAO = _python_transcricao()
IDIOMA = os.environ.get("VIDEOS_IDIOMA", "pt").strip() or "pt"

# Gerador de imagem — OPCIONAL. Capa e arte da tela dividida só existem com ele.
# O contrato está no README: `gerador "<prompt>" <saida.png> [referencia ...]`,
# sai com código 0 e o arquivo escrito.
_gerador = os.environ.get("VIDEOS_GERADOR_IMAGEM", "").strip()
GERADOR_IMAGEM: Path | None = Path(_gerador).expanduser() if _gerador else None


def gerador_ok() -> bool:
    g = GERADOR_IMAGEM
    return g is not None and g.is_file() and os.access(g, os.X_OK)


def motivo_sem_gerador() -> str:
    if GERADOR_IMAGEM is None:
        return ("Capa e arte de tela dividida estão desligadas: nenhum gerador de "
                "imagem configurado (VIDEOS_GERADOR_IMAGEM). O resto do editor "
                "funciona normalmente.")
    return (f"O gerador de imagem configurado não existe ou não é executável: "
            f"{GERADOR_IMAGEM}. Confira VIDEOS_GERADOR_IMAGEM.")


# Assinatura pequena que o gerador põe na capa (ex.: "@seuperfil"). Vazio = sem.
ASSINATURA_CAPA = os.environ.get("VIDEOS_ASSINATURA_CAPA", "").strip()

# A IA que propõe o corte roda pelo Claude Code (`claude -p`). OPCIONAL: sem
# ele o corte automático continua — só não vem a sugestão de falas a tirar.
CLAUDE_BIN = (os.environ.get("VIDEOS_CLAUDE_BIN", "").strip()
              or shutil.which("claude") or "")
IA_MODELO = os.environ.get("VIDEOS_IA_MODELO", "claude-sonnet-5").strip()


def ia_ok() -> bool:
    return bool(CLAUDE_BIN) and Path(CLAUDE_BIN).exists()


# Servidor
TOKEN = os.environ.get("VIDEOS_TOKEN", "").strip()
ORIGENS = [o.strip() for o in os.environ.get("VIDEOS_ORIGENS", "").split(",") if o.strip()]
TAM_MAX = int(os.environ.get("VIDEOS_TAM_MAX_MB", "500")) * 1024 * 1024
# Link "voltar" no topo do editor, pra quem embute a tela num painel próprio.
# Vazio = o link não aparece.
VOLTAR_URL = os.environ.get("VIDEOS_VOLTAR_URL", "").strip()
