#!/usr/bin/env python3
"""Serve o editor — a linha do tempo com a agulha, nascida do edvid.

Monta em /editor/{id}/ as mesmas rotas que o `preview_server.py` do edvid
serve localmente, mas por vídeo e sem subir um processo por vídeo.

---------------------------------------------------------------------------
POR QUE SERVIR O DELE EM VEZ DE FAZER O NOSSO

A tela do edvid tem 128 KB de HTML/CSS/JS já prontos: régua, agulha, faixas de
vídeo/áudio/legenda, forma de onda desenhada dos picos reais e miniaturas.
Reescrever isso levaria semanas e sairia pior. É MIT (© Creator Factory), e a
atribuição está em editor-ui/LICENSE-edvid, que viaja junto com a tela.

O que NÃO dá pra trazer é o servidor dele. O `preview_server.py` foi feito pra
rodar local, um processo por pasta, ao lado de um agente de terminal que fica
vigiando arquivo. Aqui existe uma API só, várias pessoas, e o vídeo é
endereçado por id. Então as ROTAS foram refeitas; a TELA é a dele, intacta.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

# A interface e NOSSA copia, adaptada. O original (MIT, (c) Creator Factory)
# continua no edvid, em assets/preview/; a licenca viajou junto em
# editor-ui/LICENSE-edvid, que e o que a MIT exige.
#
# Copiar em vez de sobrescrever por CSS foi decisao de produto: a documentacao
# do edvid trata o app de preview como imutavel, e folha injetada so muda cor e
# posicao. Pra mudar COMPORTAMENTO — que e o plano — o arquivo precisa ser nosso.
APP = Path(__file__).resolve().parent / "editor-ui"
TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css",
         ".js": "application/javascript", ".png": "image/png",
         ".jpg": "image/jpeg", ".json": "application/json",
         ".svg": "image/svg+xml"}

# O estado por extenso. O que a pessoa le tem que ser uma frase, nao um enum.
FRASE = {
    "cortando": "Estou cortando os silêncios. Já volto.",
    "aprovar_corte": "Veja o corte e diga se pode seguir.",
    "corte_ok": "Corte aprovado. Escolha o estilo quando quiser.",
    "aprovar_final": "O vídeo com legenda está pronto pra você aprovar.",
    "aprovado": "Aprovado e guardado.",
}

router = APIRouter()

_pasta = None      # injetado pelo servidor: (vid) -> Path
_ler = None        # injetado pelo servidor: (vid) -> dict | None


def ligar(pasta_fn, ler_fn) -> None:
    global _pasta, _ler
    _pasta, _ler = pasta_fn, ler_fn


def _dir(vid: str) -> Path:
    if _ler is None or _ler(vid) is None:
        raise HTTPException(404, "vídeo não encontrado")
    return _pasta(vid)


def _dentro(base: Path, rel: str) -> Path:
    """Impede que ..%2f na URL leia arquivo de fora da pasta do vídeo."""
    p = (base / rel).resolve()
    if not p.is_relative_to(base.resolve()):
        raise HTTPException(403, "caminho inválido")
    return p


def duracao(v: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(v)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# A tela lê a onda assim: {"peaksPerSec": n, "max": [...], "min": [...]}, com
# os valores em PORCENTAGEM (-100 a 100) e um par por fatia de tempo fixa.
#
# Escrevi diferente na primeira versao — {"peaks": [[min, max], ...]} com os
# valores em -1..1 — e o resultado foi uma faixa de audio vazia desde sempre:
# `S.wave.max` nao existia, o laco nao desenhava nada e nao havia erro nenhum
# no console. Formato de arquivo entre duas partes so se confere desenhando.
PICOS_POR_SEG = 20
TAXA = 8000


def gerar_waveform(video: Path, destino: Path) -> None:
    """Picos do áudio, min/max por fatia. É o desenho da faixa de som."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    wav = destino.parent / "audio.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video),
                    "-ac", "1", "-ar", str(TAXA), "-f", "wav", str(wav)],
                   capture_output=True, timeout=600)
    altos: list[int] = []
    baixos: list[int] = []
    with wave.open(str(wav), "rb") as w:
        fatia = max(1, w.getframerate() // PICOS_POR_SEG)
        while True:
            quadro = w.readframes(fatia)
            if not quadro:
                break
            amostras = [int.from_bytes(quadro[i:i + 2], "little", signed=True)
                        for i in range(0, len(quadro) - 1, 2)]
            if not amostras:
                break
            altos.append(round(max(amostras) * 100 / 32768))
            baixos.append(round(min(amostras) * 100 / 32768))
    wav.unlink(missing_ok=True)
    destino.write_text(json.dumps({"peaksPerSec": PICOS_POR_SEG,
                                   "max": altos, "min": baixos,
                                   "count": len(altos)}))


# ------------------------------------------------------------------ rotas

@router.get("/editor")
@router.get("/editor/{vid}")
def abrir(req: Request, vid: str = ""):
    """Abre o editor no vídeo escolhido (ou na Fila, sem vídeo).

    O app do edvid pede TUDO em caminho absoluto (/assets/app.css, /api/state).
    Montar em /editor/<id>/ fazia o navegador pedir na raiz do domínio e não
    achar nada — a tela subia crua, sem estilo, dizendo que esperava o render.
    Por isso o vídeo vai num cookie e o app mora na raiz, como ele espera."""
    if vid:
        _dir(vid)
    r = HTMLResponse(_html(), headers=SEM_CACHE)
    if vid:
        # Em HTTPS: samesite=none + secure. Sem isso o navegador NÃO manda o
        # cookie quando o editor está embutido num painel de outro domínio, e
        # a tela subiria pedindo pra "abrir pelo painel" dentro do painel.
        #
        # Em HTTP (rodando local, ou por IP na rede de casa) cookie `secure` é
        # recusado pelo navegador — fora do localhost ele simplesmente não é
        # gravado, e o editor abre sem vídeo nenhum. Aí vale lax, sem secure.
        https = (req.url.scheme == "https"
                 or req.headers.get("x-forwarded-proto", "") == "https")
        r.set_cookie("fd_video", vid, max_age=86400,
                     samesite="none" if https else "lax", secure=https, path="/")
    return r


def _do_cookie(req: Request) -> str:
    vid = req.cookies.get("fd_video", "")
    if not vid:
        raise HTTPException(400, "escolha um vídeo na Fila primeiro (abra /editor)")
    return vid


@router.get("/")
def raiz(req: Request):
    # Sem vídeo escolhido, a raiz leva pra Fila em vez de dar erro: é o
    # endereço que a pessoa digita depois de subir o servidor.
    if not req.cookies.get("fd_video"):
        return RedirectResponse("/editor", status_code=303)
    return HTMLResponse(_html(), headers=SEM_CACHE)


def _html() -> str:
    """O index da nossa cópia, com a versão dos arquivos carimbada na URL.

    Sem isso o navegador guarda app.css e app.js e continua desenhando a tela
    velha — a tela antiga ficou aparecendo uma manha inteira depois de ja ter
    mudado, e nao havia como saber olhando o servidor: aqui estava certo.
    Mandar dar F5 forte nao e conserto; e pedir pra pessoa lembrar de um
    detalhe nosso. O mtime muda quando o arquivo muda, e so entao."""
    h = (APP / "index.html").read_text(encoding="utf-8")
    for arq in ("app.css", "app.js"):
        try:
            v = int((APP / arq).stat().st_mtime)
        except OSError:
            continue
        h = h.replace(f"/assets/{arq}", f"/assets/{arq}?v={v}")
    return h


# A casca nunca fica em cache: e ela que carrega a versao dos outros arquivos.
SEM_CACHE = {"Cache-Control": "no-store, must-revalidate"}


@router.get("/assets/{arquivo}")
def estatico(arquivo: str):
    p = _dentro(APP, arquivo)
    if not p.exists():
        raise HTTPException(404, "não achei")
    return FileResponse(p, media_type=TIPOS.get(p.suffix, "application/octet-stream"))


@router.get("/api/state")
def estado(req: Request):
    vid = _do_cookie(req)
    d = _dir(vid)
    video = d / "corte.mp4"
    edl = None
    try:
        edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    e = _ler(vid) or {}
    arquivos = {}
    for chave, relativo in {
        "editData": "fase2/public/edit-data.json",
        "captions": "fase2/public/captions.json",
        "finalVideo": f"final-{e['ultimo_estilo']}.mp4" if e.get("ultimo_estilo") else "final.mp4",
    }.items():
        if (d / relativo).is_file():
            arquivos[chave] = relativo
    if "finalVideo" not in arquivos and (d / "final.mp4").is_file():
        arquivos["finalVideo"] = "final.mp4"
    return JSONResponse(headers=SEM_CACHE, content={
        # O id vai junto: em tela cheia nao ha painel em volta pra aplicar a
        # edicao, entao a propria tela precisa saber em quem mexer.
        "videoId": vid,
        "state": {
            "project": e.get("nome", vid),
            "phase": 2 if e.get("tem_legenda") or arquivos else 1,
            **arquivos,
            "video": "cut.mp4",
            "edl": "edl.json",
            "fps": 30,
            # A tela mostra isso pra ELA. `fase` e nome interno de estado —
            # "aprovar_corte" na cara da pessoa e vazamento de banco de dados.
            "message": FRASE.get(e.get("fase", ""), ""),
            "awaitingStyle": False,
        },
        "edl": edl,
        "mtimes": {"video": video.stat().st_mtime if video.exists() else 0,
                   **{k: (d / v).stat().st_mtime for k, v in arquivos.items()}},
        "videoDuration": duracao(video) if video.exists() else 0,
        "hasPendingEdits": (d / "preview_edits.json").exists(),
        "now": None,
    })


@router.get("/media/{arquivo:path}")
def media(req: Request, arquivo: str):
    vid = _do_cookie(req)
    # O app pede sempre "cut.mp4"; aqui o arquivo se chama corte.mp4.
    if arquivo == "cut.mp4":
        arquivo = "corte.mp4"
    p = _dentro(_dir(vid), arquivo)
    if not p.exists():
        raise HTTPException(404, "não achei")
    # FileResponse já responde Range, que é o que o arrastar da agulha usa.
    return FileResponse(p, media_type=TIPOS.get(p.suffix, "video/mp4"))


@router.get("/gen/waveform.json")
def waveform(req: Request):
    d = _dir(_do_cookie(req))
    video = d / "corte.mp4"
    if not video.exists():
        raise HTTPException(404, "sem vídeo")
    cache = d / ".preview" / "waveform.json"
    if not cache.exists() or cache.stat().st_mtime < video.stat().st_mtime:
        gerar_waveform(video, cache)
    return FileResponse(cache, media_type="application/json")


@router.get("/gen/thumbs/meta")
def thumbs_meta(req: Request):
    video = _dir(_do_cookie(req)) / "corte.mp4"
    if not video.is_file():
        raise HTTPException(404, "O corte ainda não existe. Aguarde a etapa de corte.")
    segundos = duracao(video)
    if not math.isfinite(segundos) or segundos <= 0:
        raise HTTPException(422, "Não consegui medir o corte. Confira o vídeo e refaça o corte.")
    # Índice zero: n representa o segundo n * 2, nunca (n - 1) * 2.
    return {"count": math.ceil(segundos / 2), "interval": 2}


@router.get("/gen/thumbs/{n}.jpg")
def thumb(req: Request, n: int):
    d = _dir(_do_cookie(req))
    video = d / "corte.mp4"
    if not video.exists():
        raise HTTPException(404, "sem vídeo")
    if n < 0 or n * 2 >= duracao(video):
        raise HTTPException(404, "Miniatura fora do vídeo. Atualize a página.")
    destino = d / ".preview" / f"t{n}.jpg"
    if not destino.exists() or destino.stat().st_mtime < video.stat().st_mtime:
        destino.unlink(missing_ok=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(n * 2),
                        "-i", str(video), "-frames:v", "1", "-vf", "scale=-2:90",
                        str(destino)], capture_output=True, timeout=120)
    if not destino.exists():
        raise HTTPException(404, "não consegui gerar")
    return FileResponse(destino, media_type="image/jpeg")


@router.post("/api/save")
async def salvar(req: Request):
    """A tela salva aqui o que ela marcou. Guarda e não aplica.

    Aplicar sozinho tiraria da pessoa o controle: o edvid separa salvar de
    renderizar de propósito, e o mesmo vale aqui."""
    d = _dir(_do_cookie(req))
    try:
        corpo = await req.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "JSON inválido")
    nome = ("preview_style.json" if corpo.get("type") == "style-setup"
            else "preview_edits.json")
    tmp = d / f"{nome}.tmp"
    tmp.write_text(json.dumps(corpo, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / nome)
    return {"ok": True}
