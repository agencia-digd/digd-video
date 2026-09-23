#!/usr/bin/env python3
"""dig.D Vídeo — a API: recebe o vídeo, corta os silêncios, devolve pronto.

Serve também a tela do editor (ver editor.py). Configuração em config.py.

    POST /api/videos          multipart: arquivo  -> {id}
    GET  /api/videos                              -> a fila inteira
    GET  /api/videos/{id}                         -> um item
    GET  /api/videos/{id}/original                -> o que foi enviado
    GET  /api/videos/{id}/corte                   -> o resultado
    DELETE /api/videos/{id}                       -> apaga item e arquivos

---------------------------------------------------------------------------
POR QUE ASSIM

1. UM VÍDEO POR VEZ. O corte é ffmpeg puro e come CPU inteira; dois em
   paralelo numa máquina compartilhada fazem os dois demorarem o dobro e ainda
   competem com o resto que roda nela. A fila é serial de propósito: quem
   chega espera, e o estado diz "na fila" em vez de mentir que está rodando.

2. O ESTADO VIVE EM DISCO, um JSON por vídeo, gravado com troca atômica. Se o
   serviço reiniciar no meio, a fila não some — o item volta como "erro" com a
   mensagem, em vez de sumir calado e a pessoa ficar esperando pra sempre.

3. NADA É APAGADO SOZINHO. Nem o original nem o corte. Espaço em disco é
   barato; vídeo que a pessoa gravou uma vez, não. Quem apaga é ela, no botão.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import hmac
import json
import re
import secrets
import shutil
import subprocess
import sys
import threading
import queue
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

import config

RAIZ = config.RAIZ
TRABALHOS = RAIZ / "videos"
PROCESSADOR = Path(__file__).resolve().parent / "processar.py"
FASE2 = Path(__file__).resolve().parent / "fase2.py"
FALAS = Path(__file__).resolve().parent / "falas.py"
SUGERIR = Path(__file__).resolve().parent / "sugerir.py"
APLICAR = Path(__file__).resolve().parent / "aplicar.py"
CAPA = Path(__file__).resolve().parent / "capa.py"
COM_CAPA = Path(__file__).resolve().parent / "com_capa.py"
REFS_CAPA = config.REFERENCIAS
# Os scripts da fila rodam no MESMO Python do servidor — o que está com as
# dependências instaladas. "python3" solto pegaria o do sistema.
PY = sys.executable


def _familias() -> list[dict]:
    """As linguagens de capa aprovadas. Sao varias de proposito."""
    if not REFS_CAPA.exists():
        return []
    padrao = _familia_padrao()
    return [{"nome": p.stem, "padrao": p.stem == padrao,
             "em": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()}
            for p in sorted(REFS_CAPA.glob("*.png"))]


def _familia_padrao() -> str:
    try:
        return (REFS_CAPA / "padrao.txt").read_text(encoding="utf-8").strip() or "colagem"
    except OSError:
        return "colagem"


def _slug(t: str) -> str:
    import re
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", t or "")
                if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:24] or "capa"

# A FASE e o que a PESSOA ve; o status e o estado tecnico. Separar os dois
# evita a tela dizer "processando" quando o que falta e ela apertar um botao.
#
#   cortando       a IA esta lendo e propondo o corte
#   aprovar_corte  o corte esta pronto e espera o SIM dela
#   corte_ok       aprovado; pode escolher estilo
#   aprovar_final  renderizado e esperando o SIM final
#   aprovado       entra em "Videos prontos"
FASES = ("cortando", "aprovar_corte", "corte_ok", "aprovar_final", "aprovado")
LEGENDAS = ("karaoke", "stacked", "scatter", "simples", "serifada", "classica")
HEADLINES = ("outline", "card", "realce", "misto")
TOKEN = config.TOKEN
TAM_MAX = config.TAM_MAX

TRABALHOS.mkdir(parents=True, exist_ok=True)

EXTENSOES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}

app = FastAPI(title="dig.D Vídeo")
# CORS só importa pra quem chama a API de OUTRO domínio (um painel próprio). O
# editor é servido por esta mesma API e não precisa disso.
if config.ORIGENS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ORIGENS,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        allow_credentials=True,
    )


# --------------------------------------------------------------------- acesso
#
# Com VIDEOS_TOKEN definido, TODA rota exige o token — a API, o editor e os
# arquivos de vídeo. Sem ele, qualquer um que alcance a porta vê, baixa e apaga
# os vídeos; por isso o padrão de escuta é 127.0.0.1 (ver README).
#
# O navegador não manda cabeçalho Authorization numa tag <video> nem num link
# de download, então o token também vale como cookie: abrir /entrar?token=...
# uma vez grava o cookie e o resto da tela funciona sem saber de token nenhum.
COOKIE_TOKEN = "dv_token"
LIVRES = {"/api/saude", "/entrar"}


def _token_confere(valor: str | None) -> bool:
    return bool(valor) and hmac.compare_digest(valor.encode(), TOKEN.encode())


@app.middleware("http")
async def exigir_token(req: Request, seguir):
    if not TOKEN or req.url.path in LIVRES or req.method == "OPTIONS":
        return await seguir(req)
    cab = req.headers.get("authorization", "")
    if _token_confere(cab.removeprefix("Bearer ").strip() if cab.startswith("Bearer ") else None) \
            or _token_confere(req.cookies.get(COOKIE_TOKEN)):
        return await seguir(req)
    if "text/html" in req.headers.get("accept", ""):
        return HTMLResponse(
            "<meta charset=utf-8><title>dig.D Vídeo</title>"
            "<p style='font-family:sans-serif'>Este editor pede o token de acesso. "
            "Abra <code>/entrar?token=SEU_TOKEN</code> uma vez neste navegador.</p>",
            status_code=401)
    return JSONResponse({"detail": "não autorizado"}, status_code=401)


@app.get("/entrar")
def entrar(req: Request, token: str = ""):
    """Troca o token da URL por um cookie e leva pro editor."""
    if not TOKEN:
        return RedirectResponse("/editor", status_code=303)
    if not _token_confere(token):
        raise HTTPException(401, "token errado")
    r = RedirectResponse("/editor", status_code=303)
    r.set_cookie(COOKIE_TOKEN, TOKEN, max_age=30 * 86400, httponly=True,
                 samesite="lax", secure=req.url.scheme == "https", path="/")
    return r


fila: "queue.Queue[str]" = queue.Queue()


# --------------------------------------------------------------------- estado

def _duracao(v: Path) -> float | None:
    """Duração real do arquivo, ou None se não der pra medir."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(v)],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (ValueError, subprocess.SubprocessError):
        return None


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pasta(vid: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", vid):
        raise HTTPException(404, "vídeo não encontrado")
    return TRABALHOS / vid


def ler(vid: str) -> dict | None:
    p = pasta(vid) / "estado.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def gravar(vid: str, estado: dict) -> None:
    d = pasta(vid)
    d.mkdir(parents=True, exist_ok=True)
    estado["atualizado_em"] = agora()
    tmp = d / "estado.tmp"
    tmp.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / "estado.json")


def todos() -> list[dict]:
    itens = []
    for d in TRABALHOS.iterdir():
        if not d.is_dir():
            continue
        e = ler(d.name)
        if e:
            # A tela precisa saber se ja existe a versao com a capa colada na
            # frente — e o arquivo que vai pro Instagram.
            e["com_capa"] = (d / "final-com-capa.mp4").exists()
            itens.append(e)
    return sorted(itens, key=lambda x: x.get("criado_em", ""), reverse=True)


# --------------------------------------------------------------------- worker

def trabalhador() -> None:
    """Consome a fila, um vídeo por vez, pra sempre."""
    while True:
        vid = fila.get()
        try:
            estado = ler(vid)
            if not estado or estado.get("status") not in ("na_fila",):
                continue
            proximo = estado.get("proximo")
            automatico = proximo == "auto"
            legendando = proximo == "legenda"
            preparando = proximo == "falas"
            recortando = proximo == "recorte"
            aplicando = proximo == "aplicar"
            fazendo_split = proximo == "split"
            fazendo_capa = proximo == "capa"
            colando_capa = proximo == "capa_frente"
            estado["status"] = "processando"
            estado["etapa"] = ("lendo o que você falou" if automatico
                               else "escrevendo as legendas" if legendando
                               else "lendo o que você falou" if preparando
                               else "desenhando as artes da tela dividida" if fazendo_split
                               else "desenhando a capa" if fazendo_capa
                               else "colando a capa na frente" if colando_capa
                               else "aplicando o que você marcou" if aplicando
                               else "remontando o corte" if recortando
                               else "analisando o áudio")
            estado.pop("proximo", None)
            gravar(vid, estado)

            d = pasta(vid)
            if legendando:
                e = estado.get("estilo", {})
                cmd = [PY, str(FASE2), "--dir", str(d),
                       "--legenda", e.get("legenda", "karaoke")]
                if e.get("headline") and e.get("linhas"):
                    cmd += ["--headline", e["headline"], "--linhas", *e["linhas"]]
                    if e.get("headline_escala"):
                        cmd += ["--headline-escala", str(e["headline_escala"])]
                if e.get("zoom_cortes"):
                    cmd.append("--zoom-cortes")
                if e.get("zoom_auto"):
                    cmd.append("--zoom-auto")
                if e.get("rosto"):
                    cmd.append("--rosto")
                if e.get("flash"):
                    cmd.append("--flash")
                if e.get("trilha"):
                    cmd += ["--trilha", e["trilha"]]
                if e.get("fonte_escala"):
                    cmd += ["--fonte-escala", str(e["fonte_escala"])]
                if e.get("legenda_subir"):
                    cmd += ["--legenda-subir", str(e["legenda_subir"])]
                if (d / "split.json").exists():
                    cmd += ["--tela-dividida", str(d / "split.json")]
                if e.get("fechamento"):
                    cmd += ["--fechamento", e["fechamento"],
                            "--fechamento-antes", e.get("fechamento_antes", "digita"),
                            "--fechamento-depois", e.get("fechamento_depois", "aqui embaixo")]
            elif automatico:
                cmd = [PY, str(FALAS), "--dir", str(d)]
            elif preparando:
                cmd = [PY, str(FALAS), "--dir", str(d)]
            elif aplicando:
                cmd = [PY, str(APLICAR), "--dir", str(d)]
            elif colando_capa:
                cmd = [PY, str(COM_CAPA), "--dir", str(d),
                       "--capa", estado.get("capa_na_frente", "")]
            elif fazendo_split:
                pedido = json.loads((d / "split.pedido.json").read_text(encoding="utf-8"))
                cmd = [PY, str(ARTE_SPLIT), "--dir", str(d),
                       "--familia", pedido["familia"], "--plano", str(d / "split.pedido.json")]
            elif fazendo_capa:
                cmd = [PY, str(CAPA), "--dir", str(d),
                       "--frase", estado.get("capa_frase", "")]
                if estado.get("capa_familia"):
                    cmd += ["--familia", estado["capa_familia"]]
            elif recortando:
                # monta o EDL do que ficou e refaz o corte a partir dele
                cmd = [PY, str(FALAS), "--dir", str(d), "--montar"]
            else:
                cmd = [PY, str(PROCESSADOR), str(d / "entrada.mp4"),
                       "--saida-dir", str(d)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5400)
            saida = (proc.stdout or "") + (proc.stderr or "")

            if automatico and proc.returncode == 0:
                # a IA le e propoe; depois monta e renderiza o corte proposto
                estado["etapa"] = "a IA está escolhendo os cortes"
                gravar(vid, estado)
                proc = subprocess.run([PY, str(SUGERIR), "--dir", str(d)],
                                      capture_output=True, text=True, timeout=1800)
                saida += (proc.stdout or "") + (proc.stderr or "")
                if proc.returncode == 0:
                    estado["etapa"] = "montando o corte"
                    gravar(vid, estado)
                    proc = subprocess.run([PY, str(FALAS), "--dir", str(d),
                                           "--montar"],
                                          capture_output=True, text=True, timeout=600)
                    saida += (proc.stdout or "") + (proc.stderr or "")

            if (recortando or automatico or aplicando) and proc.returncode == 0:
                # o EDL novo existe; agora renderiza o corte a partir dele
                proc = subprocess.run(
                    [PY, str(PROCESSADOR), str(d / "entrada.mp4"),
                     "--saida-dir", str(d), "--do-edl"],
                    capture_output=True, text=True, timeout=5400)
                saida += (proc.stdout or "") + (proc.stderr or "")

            corte = d / "corte.mp4"
            final = d / "final.mp4"
            alvo = ((d / "split.json") if fazendo_split else final if legendando
                    else (d / "falas.json") if preparando
                    else corte)
            if proc.returncode == 0 and alvo.exists():
                estado["status"] = "pronto"
                estado.pop("etapa", None)
                if legendando:
                    # Um arquivo POR ESTILO. Antes o render novo sobrescrevia o
                    # anterior, e comparar dois estilos exigia copiar na mão —
                    # que é exatamente o que a tela precisa fazer sozinha.
                    est = estado.get("estilo", {}).get("legenda", "karaoke")
                    guardado = d / f"final-{est}.mp4"
                    final.replace(guardado)
                    versoes = {v["estilo"]: v for v in estado.get("versoes", [])}
                    versoes[est] = {
                        "estilo": est,
                        "tamanho": guardado.stat().st_size,
                        "em": agora(),
                        "zoom_cortes": bool(estado.get("estilo", {}).get("zoom_cortes")),
                    }
                    estado["versoes"] = sorted(versoes.values(), key=lambda v: v["em"])
                    estado["tem_legenda"] = True
                    estado["ultimo_estilo"] = est
                    estado["tamanho_saida"] = guardado.stat().st_size
                # Os numeros saem do ARQUIVO, nao do texto do log. Ler o log
                # dava 54s quando o corte tinha 41,4s: a linha vinha do corte
                # automatico antigo e o recorte por texto nem imprime esse
                # formato. Medir o que existe nao tem como envelhecer.
                if corte.exists():
                    estado["tamanho_saida"] = corte.stat().st_size
                    d_corte = _duracao(corte)
                    d_orig = _duracao(d / "entrada.mp4")
                    if d_corte and d_orig:
                        estado["dur_final"] = round(d_corte, 1)
                        estado["dur_original"] = round(d_orig, 1)
                        estado["cortado_pct"] = int(round((1 - d_corte / d_orig) * 100))
                    try:
                        estado["trechos"] = len(json.loads(
                            (d / "edl.json").read_text(encoding="utf-8"))["ranges"])
                    except (OSError, json.JSONDecodeError, KeyError):
                        pass
            else:
                estado["status"] = "erro"
                estado.pop("etapa", None)
                ultima = [l for l in saida.strip().splitlines() if l.strip()]
                estado["erro"] = (ultima[-1][:300] if ultima
                                  else "o processamento falhou sem dizer por quê")
            if estado.get("status") == "pronto":
                if legendando:
                    estado["fase"] = "aprovar_final"
                elif automatico or recortando or aplicando:
                    estado["fase"] = "aprovar_corte"
            gravar(vid, estado)
        except subprocess.TimeoutExpired:
            e = ler(vid) or {}
            e.update(status="erro", erro="passou de 1 hora processando e foi parado")
            e.pop("etapa", None)
            gravar(vid, e)
        except Exception as exc:  # noqa: BLE001 — falha vira estado legível
            e = ler(vid) or {}
            e.update(status="erro", erro=f"{type(exc).__name__}: {exc}"[:300])
            e.pop("etapa", None)
            gravar(vid, e)
        finally:
            fila.task_done()


def retomar_pendentes() -> None:
    """Depois de um restart: o que ficou 'processando' virou órfão."""
    for e in todos():
        if e.get("status") == "processando":
            e["status"] = "erro"
            e["erro"] = "o serviço reiniciou no meio. Dá pra mandar de novo."
            e.pop("etapa", None)
            gravar(e["id"], e)
        elif e.get("status") == "na_fila":
            fila.put(e["id"])


@app.on_event("startup")
def subir() -> None:
    threading.Thread(target=trabalhador, daemon=True).start()
    retomar_pendentes()


# ---------------------------------------------------------------------- rotas

@app.get("/api/recursos")
def recursos():
    """O que está ligado nesta instalação. A tela usa pra avisar em vez de quebrar."""
    return {
        "capa": config.gerador_ok(),
        "arte": config.gerador_ok(),
        "motivo_imagem": None if config.gerador_ok() else config.motivo_sem_gerador(),
        "ia": config.ia_ok(),
        "voltar": config.VOLTAR_URL or None,
    }


def _exigir_gerador() -> None:
    if not config.gerador_ok():
        raise HTTPException(503, config.motivo_sem_gerador())


@app.post("/api/videos")
async def enviar(arquivo: UploadFile = File(...)):
    nome = Path(arquivo.filename or "video.mp4").name
    if Path(nome).suffix.lower() not in EXTENSOES:
        raise HTTPException(400, f"formato não aceito. Use: {', '.join(sorted(EXTENSOES))}")

    vid = secrets.token_urlsafe(9)
    d = pasta(vid)
    d.mkdir(parents=True, exist_ok=True)
    destino = d / "entrada.mp4"

    total = 0
    with destino.open("wb") as f:
        while pedaco := await arquivo.read(1024 * 1024):
            total += len(pedaco)
            if total > TAM_MAX:
                f.close()
                shutil.rmtree(d, ignore_errors=True)
                raise HTTPException(413, f"vídeo maior que {TAM_MAX // 1024 // 1024} MB")
            f.write(pedaco)

    if total == 0:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(400, "o arquivo chegou vazio")

    gravar(vid, {
        "id": vid, "nome": nome, "status": "na_fila",
        "fase": "cortando", "proximo": "auto",
        "tamanho": total, "criado_em": agora(),
    })
    fila.put(vid)
    return {"id": vid}


@app.get("/api/videos")
def listar():
    return JSONResponse({"itens": todos(), "na_fila": fila.qsize()})


@app.get("/api/videos/{vid}")
def um(vid: str):
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    return JSONResponse(e)


@app.get("/api/videos/{vid}/corte")
def baixar_corte(vid: str):
    e = ler(vid)
    if not e or e.get("status") != "pronto":
        raise HTTPException(404, "esse corte ainda não existe")
    p = pasta(vid) / "corte.mp4"
    if not p.exists():
        raise HTTPException(404, "arquivo sumiu do disco")
    base = Path(e.get("nome", "video")).stem
    return FileResponse(p, media_type="video/mp4", filename=f"{base}-cortado.mp4")


@app.get("/api/videos/{vid}/final")
def baixar_final(vid: str):
    e = ler(vid)
    if not e or not e.get("tem_legenda"):
        raise HTTPException(404, "esse ainda não foi legendado")
    ultimo = e.get("ultimo_estilo")
    p = pasta(vid) / (f"final-{ultimo}.mp4" if ultimo else "final.mp4")
    if not p.exists():
        p = pasta(vid) / "final.mp4"
    if not p.exists():
        raise HTTPException(404, "arquivo sumiu do disco")
    base = Path(e.get("nome", "video")).stem
    return FileResponse(p, media_type="video/mp4", filename=f"{base}-legendado.mp4")


@app.get("/api/videos/{vid}/versao/{estilo}")
def baixar_versao(vid: str, estilo: str):
    if estilo not in LEGENDAS:
        raise HTTPException(404, "estilo desconhecido")
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    p = pasta(vid) / f"final-{estilo}.mp4"
    if not p.exists():
        raise HTTPException(404, "esse estilo ainda não foi renderizado")
    base = Path(e.get("nome", "video")).stem
    return FileResponse(p, media_type="video/mp4", filename=f"{base}-{estilo}.mp4")


@app.post("/api/videos/{vid}/aprovar")
def aprovar(vid: str, decisao: dict):
    """Os dois portões: o corte e o vídeo final.

    `etapa` diz qual portão ("corte" ou "final") e `ok` diz sim ou não.
    Recusar não apaga nada — devolve pra edição, que é onde ela conserta."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    etapa = decisao.get("etapa")
    ok = bool(decisao.get("ok"))
    motivo = str(decisao.get("motivo") or "")[:300]

    if etapa == "corte":
        if e.get("fase") != "aprovar_corte":
            raise HTTPException(409, "este vídeo não está esperando aprovação de corte")
        e["fase"] = "corte_ok" if ok else "aprovar_corte"
        if not ok:
            # Recusar mantém o corte no lugar de propósito: ela ajusta o que
            # não gostou em cima dele, em vez de recomeçar do zero.
            e["corte_recusado"] = {"em": agora(), "motivo": motivo}
        else:
            e.pop("corte_recusado", None)
    elif etapa == "final":
        if e.get("fase") != "aprovar_final":
            raise HTTPException(409, "este vídeo não está esperando aprovação final")
        e["fase"] = "aprovado" if ok else "corte_ok"
        if ok:
            e["aprovado_em"] = agora()
        else:
            e["final_recusado"] = {"em": agora(), "motivo": motivo}
    else:
        raise HTTPException(400, "etapa tem que ser 'corte' ou 'final'")

    gravar(vid, e)
    return {"ok": True, "fase": e["fase"]}


@app.get("/api/videos/{vid}/falas")
def ler_falas(vid: str):
    """Os blocos de fala pra tela de edição por texto."""
    if not ler(vid):
        raise HTTPException(404, "vídeo não encontrado")
    p = pasta(vid) / "falas.json"
    if not p.exists():
        raise HTTPException(404, "ainda não preparei as falas deste vídeo")
    return JSONResponse(json.loads(p.read_text(encoding="utf-8")))


@app.post("/api/videos/{vid}/preparar-falas")
def preparar_falas(vid: str):
    """Transcreve o ORIGINAL e monta os blocos editáveis."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")
    e["status"] = "na_fila"
    e["proximo"] = "falas"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


@app.post("/api/videos/{vid}/recortar")
def recortar(vid: str, marcacao: dict):
    """Refaz o corte com o que ela marcou no texto."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    p = pasta(vid) / "falas.json"
    if not p.exists():
        raise HTTPException(409, "as falas ainda não foram preparadas")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")

    dados = json.loads(p.read_text(encoding="utf-8"))
    validos = {b["id"] for b in dados["blocos"]}
    fora = [x for x in (marcacao.get("retirados") or []) if x in validos]
    if len(fora) >= len(validos):
        raise HTTPException(400, "você tirou tudo — precisa sobrar pelo menos uma fala.")
    dados["retirados"] = fora
    dados["manter_inicio"] = bool(marcacao.get("manter_inicio"))
    try:
        dados["inicio_em"] = max(0.0, float(marcacao.get("inicio_em") or 0))
    except (TypeError, ValueError):
        dados["inicio_em"] = 0.0
    # Aparo por bloco: {"b017": {"fim": 67.72}}. Só ids que existem.
    aj = marcacao.get("ajustes") or {}
    dados["ajustes"] = {
        k: {n: float(v) for n, v in val.items() if n in ("inicio", "fim")}
        for k, val in aj.items() if k in validos and isinstance(val, dict)
    }
    try:
        dados["pausa_max"] = min(8.0, max(0.0, float(marcacao.get("pausa_max") or 0)))
    except (TypeError, ValueError):
        dados["pausa_max"] = 0.0
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    # O corte novo invalida tudo que veio depois: legenda, enfeite, versões.
    # Guardar versões de um corte que não existe mais engana quem abre a tela.
    for v in e.get("versoes", []):
        (pasta(vid) / f"final-{v['estilo']}.mp4").unlink(missing_ok=True)
    e["versoes"] = []
    e.pop("tem_legenda", None)
    e.pop("ultimo_estilo", None)
    e["status"] = "na_fila"
    e["proximo"] = "recorte"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True, "retirados": len(fora)}


@app.post("/api/videos/{vid}/aplicar-edicao")
def aplicar_edicao(vid: str):
    """Pega o que ela marcou no editor de linha do tempo e refaz o corte."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    if not (pasta(vid) / "preview_edits.json").exists():
        raise HTTPException(409, "não há edição salva no editor")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")
    for v in e.get("versoes", []):
        (pasta(vid) / f"final-{v['estilo']}.mp4").unlink(missing_ok=True)
    e["versoes"] = []
    e.pop("tem_legenda", None)
    e.pop("ultimo_estilo", None)
    e["status"] = "na_fila"
    e["proximo"] = "aplicar"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


@app.post("/api/videos/{vid}/legendar")
def legendar(vid: str, estilo: dict):
    """Fase 2: legenda, zoom, headline e trilha em cima do corte."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    if not (pasta(vid) / "corte.mp4").exists():
        raise HTTPException(409, "o corte ainda não existe. Espere a Fase 1.")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")

    legenda = estilo.get("legenda", "karaoke")
    if legenda not in LEGENDAS:
        raise HTTPException(400, f"estilo de legenda desconhecido: {legenda}")
    headline = estilo.get("headline")
    if headline and headline not in HEADLINES:
        raise HTTPException(400, f"estilo de headline desconhecido: {headline}")

    try:
        escala = float(estilo.get("fonte_escala", 1.0))
    except (TypeError, ValueError):
        escala = 1.0
    # Teto de 2,0: acima disso a legenda cobre o rosto e o vídeo fica ilegível.
    escala = min(2.0, max(0.6, escala))

    e["estilo"] = {
        "legenda": legenda,
        "headline": headline,
        "fonte_escala": escala,
        # Teto da headline, em cima do padrao de cada estilo. Fora de 0,6-2,5
        # ela some da tela ou cobre o rosto.
        "headline_escala": min(2.5, max(0.6, float(estilo.get("headline_escala") or 1.0))),
        # Quanto a legenda sobe, em fracao da tela. Teto de 0,55: da pra por
        # ACIMA DA CABECA, que foi o que ela pediu. O titulo mora la em cima
        # tambem, mas so nos primeiros 4s — os dois nao disputam o mesmo tempo.
        "legenda_subir": min(0.55, max(0.0, float(estilo.get("legenda_subir") or 0.0))),
        "fechamento": (str(estilo.get("fechamento") or "").strip()[:20]) or None,
        "fechamento_antes": (str(estilo.get("fechamento_antes") or "").strip()[:30]
                             or "digita"),
        "fechamento_depois": (str(estilo.get("fechamento_depois") or "").strip()[:30]
                              or "aqui embaixo"),
        "linhas": [str(x)[:80] for x in (estilo.get("linhas") or [])][:3],
        "zoom_cortes": bool(estilo.get("zoom_cortes")),
        "zoom_auto": bool(estilo.get("zoom_auto")),
        "rosto": bool(estilo.get("rosto")),
        "flash": bool(estilo.get("flash")),
        "trilha": estilo.get("trilha") or None,
    }
    e["status"] = "na_fila"
    e["proximo"] = "legenda"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


@app.get("/api/videos/{vid}/original")
def baixar_original(vid: str):
    p = pasta(vid) / "entrada.mp4"
    if not p.exists():
        raise HTTPException(404, "original não encontrado")
    return FileResponse(p, media_type="video/mp4")


@app.delete("/api/videos/{vid}")
def apagar(vid: str):
    d = pasta(vid)
    if not d.exists():
        raise HTTPException(404, "vídeo não encontrado")
    e = ler(vid)
    if e and e.get("status") == "processando":
        raise HTTPException(409, "esse está sendo processado agora. Espere terminar.")
    shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}


# ------------------------------------------------------------------ tela dividida
ARTE_SPLIT = Path(__file__).resolve().parent / "arte_split.py"
ARTE_REFS = config.REFERENCIAS_ARTE


@app.get("/api/arte/familias")
def familias_arte():
    if not ARTE_REFS.is_dir():
        raise HTTPException(404, "Cadastre uma família com imagens em referencias/arte antes de gerar.")
    return {"familias": sorted(p.name for p in ARTE_REFS.iterdir() if p.is_dir())}


@app.get("/api/videos/{vid}/split")
def ler_split(vid: str):
    if not ler(vid):
        raise HTTPException(404, "Vídeo não encontrado. Abra um vídeo na Fila.")
    alvo = pasta(vid) / "split.json"
    if not alvo.exists():
        return {"itens": []}
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(422, "Não consegui ler split.json. Restaure o plano anterior antes de gerar.")


@app.get("/api/videos/{vid}/split/imagem/{nome}")
def imagem_split(vid: str, nome: str):
    plano = ler_split(vid)
    arquivos = [pasta(vid) / i["arquivo"] for i in plano.get("itens", []) if i.get("arquivo")]
    alvo = next((p.resolve() for p in arquivos if p.name == nome), None)
    if alvo is None or not alvo.is_relative_to(pasta(vid).resolve()) or not alvo.is_file():
        raise HTTPException(404, "A imagem não foi encontrada. Refaça esta faixa.")
    return FileResponse(alvo)


@app.post("/api/videos/{vid}/split")
def pedir_split(vid: str, corpo: dict):
    import math
    _exigir_gerador()
    e = ler(vid)
    if not e:
        raise HTTPException(404, "Vídeo não encontrado. Abra um vídeo na Fila.")
    if e.get("status") in ("na_fila", "processando"):
        raise HTTPException(409, "Este vídeo já está na fila ou processando. Aguarde terminar.")
    d = pasta(vid)
    if not (d / "corte.mp4").exists():
        raise HTTPException(409, "O corte ainda não existe. Aguarde a etapa de corte.")
    nome = corpo.get("familia")
    if not isinstance(nome, str) or nome not in familias_arte()["familias"]:
        raise HTTPException(400, "Escolha uma família de arte cadastrada.")
    refs = ARTE_REFS / nome
    if not list(refs.glob("*.png")) + list(refs.glob("*.jpg")):
        raise HTTPException(400, "Esta família não tem imagens PNG ou JPG. Cadastre referências antes de gerar.")
    anterior = ler_split(vid)
    itens = corpo.get("itens")
    try:
        if not isinstance(itens, list) or not itens:
            raise ValueError()
        dur = _duracao(d / "corte.mp4")
        permitidos = {i.get("arquivo") for i in anterior.get("itens", [])}
        for it in itens:
            if not isinstance(it, dict):
                raise ValueError()
            ini, fim = float(it["inicio"]), float(it["fim"])
            if not all(map(math.isfinite, (ini, fim))) or not 0 <= ini < fim <= dur:
                raise ValueError()
            it["inicio"], it["fim"] = ini, fim
            if it.get("posicao", "top") not in ("top", "bottom"):
                raise ValueError()
            if not 0 < float(it.get("faixa", 750)) < 1920:
                raise ValueError()
            arq = it.get("arquivo")
            if arq:
                p = (d / arq).resolve()
                if arq not in permitidos or not p.is_relative_to(d.resolve()) or not p.is_file():
                    raise ValueError()
            if (not arq or it.get("refazer")) and not str(it.get("descricao", "")).strip():
                raise ValueError()
        enquadramento = corpo.get("enquadramento", anterior.get("enquadramento"))
        if not isinstance(enquadramento, dict) or not enquadramento:
            raise ValueError()
        for lado, valores in enquadramento.items():
            if lado not in ("top", "bottom") or not isinstance(valores, dict):
                raise ValueError()
            if not math.isfinite(float(valores["zoom"])) or float(valores["zoom"]) <= 0 or not math.isfinite(float(valores["focusY"])):
                raise ValueError()
        if any(it.get("posicao", "top") not in enquadramento for it in itens):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise HTTPException(400, "Confira início e fim dentro do corte, descrição das novas artes e enquadramento medido (zoom e focusY) para cada posição.")
    pedido = {"familia": nome, "itens": itens, "enquadramento": enquadramento}
    (d / "split.pedido.json").write_text(json.dumps(pedido, ensure_ascii=False), encoding="utf-8")
    e["status"] = "na_fila"
    e["proximo"] = "split"
    e["etapa"] = "aguardando geração das artes"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


# ------------------------------------------------------------------ capas

def _capas(vid: str) -> list[dict]:
    d = pasta(vid) / "capas"
    if not d.exists():
        return []
    refs = {p.stem: p.read_bytes() for p in REFS_CAPA.glob("*.png")}
    saida = []
    for p in sorted(d.glob("[0-9]*.png")):
        saida.append({
            "nome": p.name,
            "em": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
            "tamanho": p.stat().st_size,
            # De QUAL família esta capa é a referência, se for de alguma.
            # Comparo o conteúdo porque a referência é uma CÓPIA, não um link:
            # se fosse link, apagar o vídeo levaria junto o padrão da casa.
            "referencia": next((n for n, b in refs.items() if b == p.read_bytes()), None),
        })
    return saida


@app.get("/api/videos/{vid}/capas")
def listar_capas(vid: str):
    if not ler(vid):
        raise HTTPException(404, "vídeo não encontrado")
    return {"itens": _capas(vid), "familias": _familias(),
            "padrao": _familia_padrao()}


@app.get("/api/videos/{vid}/capa/{nome}")
def baixar_capa(vid: str, nome: str):
    p = (pasta(vid) / "capas" / nome).resolve()
    if not str(p).startswith(str((pasta(vid) / "capas").resolve())) or not p.exists():
        raise HTTPException(404, "capa não encontrada")
    return FileResponse(p, media_type="image/png")


@app.post("/api/videos/{vid}/capa")
def pedir_capa(vid: str, corpo: dict):
    """Põe uma capa na fila. A frase vem em até quatro partes, separadas por |."""
    _exigir_gerador()
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")
    frase = str(corpo.get("frase", "")).strip()
    if not frase:
        raise HTTPException(400, "preciso da frase da capa.")
    e["capa_frase"] = frase[:400]
    e["capa_familia"] = _slug(corpo.get("familia") or "") or _familia_padrao()
    e["status"] = "na_fila"
    e["proximo"] = "capa"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


@app.post("/api/videos/{vid}/capa/{nome}/referencia")
def virar_referencia(vid: str, nome: str, corpo: dict | None = None):
    """Esta capa passa a ditar o estilo das próximas.

    O padrão da casa é um ARQUIVO, não um parágrafo dentro do script: descrever
    o estilo em palavras foi o que produziu uma capa com outra pessoa. Trocar a
    referência é trocar a imagem."""
    p = (pasta(vid) / "capas" / nome).resolve()
    if not str(p).startswith(str((pasta(vid) / "capas").resolve())) or not p.exists():
        raise HTTPException(404, "capa não encontrada")
    familia = _slug((corpo or {}).get("familia") or "")
    if not familia:
        raise HTTPException(400, "preciso do nome da família (ex.: colagem, calma…).")
    REFS_CAPA.mkdir(parents=True, exist_ok=True)
    destino = REFS_CAPA / f"{familia}.png"
    tmp = destino.with_suffix(".tmp")
    tmp.write_bytes(p.read_bytes())
    tmp.replace(destino)
    return {"ok": True, "familia": familia}


@app.post("/api/videos/{vid}/capa/{nome}/na-frente")
def capa_na_frente(vid: str, nome: str):
    """Cola esta capa por 1 segundo no comeco do video.

    E o que faz a capa valer no feed: quem passa rolando ve o PRIMEIRO QUADRO
    em movimento, nao a capa que o Instagram deixa escolher."""
    e = ler(vid)
    if not e:
        raise HTTPException(404, "vídeo não encontrado")
    if e.get("status") == "processando":
        raise HTTPException(409, "esse já está sendo processado agora.")
    p = (pasta(vid) / "capas" / nome).resolve()
    if not str(p).startswith(str((pasta(vid) / "capas").resolve())) or not p.exists():
        raise HTTPException(404, "capa não encontrada")
    e["capa_na_frente"] = nome
    e["status"] = "na_fila"
    e["proximo"] = "capa_frente"
    e.pop("erro", None)
    gravar(vid, e)
    fila.put(vid)
    return {"ok": True}


@app.get("/api/videos/{vid}/com-capa")
def baixar_com_capa(vid: str):
    # A versao de ENTREGA vem primeiro, se existir: o Instagram recusou um
    # arquivo de 5,6 Mbps com "media upload has failed", e a mesma imagem a
    # 4 Mbps passou. (A publicação no Instagram não faz parte deste pacote.)
    p = pasta(vid) / "final-instagram.mp4"
    if not p.exists():
        p = pasta(vid) / "final-com-capa.mp4"
    if not p.exists():
        raise HTTPException(404, "esse ainda não tem a capa colada na frente")
    return FileResponse(p, media_type="video/mp4")


@app.post("/api/capas/padrao")
def trocar_padrao(corpo: dict):
    familia = _slug(corpo.get("familia") or "")
    if not (REFS_CAPA / f"{familia}.png").exists():
        raise HTTPException(404, "não conheço essa família de capa.")
    (REFS_CAPA / "padrao.txt").write_text(familia, encoding="utf-8")
    return {"ok": True, "padrao": familia}


@app.delete("/api/capas/referencia/{familia}")
def apagar_familia(familia: str):
    p = REFS_CAPA / f"{_slug(familia)}.png"
    if not p.exists():
        raise HTTPException(404, "não conheço essa família de capa.")
    if _familia_padrao() == p.stem:
        raise HTTPException(409, "essa é a família padrão. Escolha outra padrão antes.")
    p.unlink()
    return {"ok": True}


@app.get("/api/capas/referencia/{familia}")
def ver_referencia(familia: str):
    p = REFS_CAPA / f"{_slug(familia)}.png"
    if not p.exists():
        raise HTTPException(404, "não conheço essa família de capa.")
    return FileResponse(p, media_type="image/png")


@app.delete("/api/videos/{vid}/capa/{nome}")
def apagar_capa(vid: str, nome: str):
    p = (pasta(vid) / "capas" / nome).resolve()
    if not str(p).startswith(str((pasta(vid) / "capas").resolve())) or not p.exists():
        raise HTTPException(404, "capa não encontrada")
    p.unlink()
    return {"ok": True}


import editor as _editor
_editor.ligar(pasta, ler)
app.include_router(_editor.router)


@app.get("/api/saude")
def saude():
    return {"ok": True, "processador": PROCESSADOR.exists(), "na_fila": fila.qsize()}
