#!/usr/bin/env python3
"""Fase 1 do corte automático: tira os silêncios, acerta o volume, renderiza.

Entra um vídeo falado direto do celular, sai um corte pronto pra postar.

    python3 processar.py entrada.mp4 --saida-dir /caminho/de/trabalho

---------------------------------------------------------------------------
POR QUE ASSIM

O motor de corte é o `speech_regions.py` do edvid (MIT, © Creator Factory) —
detecção acústica de fala por `silencedetect` do ffmpeg. Ele responde ONDE a
pessoa fala. Não usa Whisper: pro corte, o que importa é onde tem voz, não o
que foi dito. Isso deixa a Fase 1 rodar em qualquer máquina, sem baixar modelo.

O render também é do edvid (`render.py`): extração por segmento e remontagem
com J-cut, que é o que faz a emenda não estalar. Escrever isso de novo seria
refazer pior o que já está pago e testado.

TRÊS DECISÕES QUE VALEM A LEITURA

1. PAUSA CURTA FICA. Só cortamos buraco de 1,2s pra cima. Fala natural tem
   pausa de respiração de 0,3 a 0,8s; cortar tudo produz aquele vídeo ofegante
   que ninguém aguenta ver. O limiar é o mesmo que o `verify_cut.py` do edvid
   usa pra reprovar dead air.

2. A BORDA GANHA FOLGA, E A DE TRÁS GANHA MAIS. 80ms antes, 140ms depois. Sem
   isso o corte come o começo da consoante e a última sílaba fica cortada — o
   "pop" clássico de corte automático malfeito.

3. O VOLUME SE MEDE POR TRECHO. Quem fala andando pela sala fica mais baixo
   longe do microfone. Medimos o RMS de cada trecho, comparamos com a mediana,
   e quem estiver abaixo ganha ganho até emparelhar. Depois o loudnorm do
   render fecha em -14 LUFS, que é o alvo de rede social.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import shutil
import subprocess
import sys
from pathlib import Path

import config

AQUI = Path(__file__).resolve().parent
EDVID = config.EDVID_HELPERS

SILENCIO_MIN = 1.2   # buraco a partir daqui é cortado
FOLGA_ANTES = 0.08
FOLGA_DEPOIS = 0.14
GANHO_MAX = 12.0     # teto: acima disso é ruído sendo amplificado, não voz


def duracao(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def regioes_de_fala(video: Path) -> list[tuple[float, float]]:
    """Chama o speech_regions.py do edvid e lê os intervalos."""
    r = subprocess.run(
        [sys.executable, str(EDVID / "speech_regions.py"), str(video)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"speech_regions falhou: {r.stderr[:300]}")
    regioes = []
    for linha in r.stdout.splitlines():
        m = re.match(r"\s*([\d.]+)\s*->\s*([\d.]+)", linha)
        if m:
            regioes.append((float(m.group(1)), float(m.group(2))))
    return regioes


def montar_trechos(regioes, dur: float) -> list[tuple[float, float]]:
    """Junta regiões separadas por pausa curta; corta só buraco >= SILENCIO_MIN."""
    if not regioes:
        return []
    trechos = [list(regioes[0])]
    for ini, fim in regioes[1:]:
        if ini - trechos[-1][1] < SILENCIO_MIN:
            trechos[-1][1] = fim          # pausa curta: mantém, é respiração
        else:
            trechos.append([ini, fim])    # buraco grande: começa trecho novo
    saida = []
    for ini, fim in trechos:
        saida.append((max(0.0, ini - FOLGA_ANTES), min(dur, fim + FOLGA_DEPOIS)))
    return saida


def rms_db(video: Path, ini: float, fim: float) -> float:
    """Volume médio de um trecho, em dB. -99 quando não dá pra medir."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{ini:.3f}",
         "-t", f"{max(0.05, fim - ini):.3f}", "-i", str(video),
         "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
        capture_output=True, text=True)
    achados = re.findall(r"RMS level dB:\s*(-?[\d.]+|-inf)", r.stderr)
    valores = [float(v) for v in achados if v != "-inf"]
    return max(valores) if valores else -99.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--saida-dir", type=Path, required=True)
    ap.add_argument("--do-edl", action="store_true",
                    help="usa o edl.json que ja existe (veio da edicao por texto)")
    ap.add_argument("--rascunho", action="store_true",
                    help="720p ultrafast — só pra conferir os pontos de corte")
    args = ap.parse_args()

    trabalho = args.saida_dir
    trabalho.mkdir(parents=True, exist_ok=True)

    origem = trabalho / "entrada.mp4"
    if origem.resolve() != args.video.resolve():
        origem.write_bytes(args.video.read_bytes())

    dur = duracao(origem)
    print(f"[1/4] entrada: {dur:.1f}s", flush=True)

    if args.do_edl:
        # O corte veio da edição por texto: o EDL já está escrito e é a decisão
        # da PESSOA. Não se recalcula silêncio aqui — isso desfaria o que ela marcou.
        if not (trabalho / "edl.json").exists():
            raise SystemExit("--do-edl mas não achei edl.json")
        saida = trabalho / "corte.mp4"
        print("[2/4] usando o corte que você marcou", flush=True)
        print("[3/4] pulando a análise de silêncio", flush=True)
        print("[4/4] renderizando…", flush=True)
        r = subprocess.run(
            [sys.executable, str(EDVID / "render.py"), str(trabalho / "edl.json"),
             "-o", str(saida), "--no-subtitles"], capture_output=True, text=True)
        if r.returncode != 0 or not saida.exists():
            print((r.stdout or "")[-1200:], file=sys.stderr)
            raise SystemExit("o render falhou.")
        for lixo in (trabalho / "clips_graded", trabalho / "clips_draft"):
            shutil.rmtree(lixo, ignore_errors=True)
        (trabalho / "base.mp4").unlink(missing_ok=True)
        final = duracao(saida)
        print(f"pronto: {saida}  ({final:.1f}s, era {dur:.1f}s)", flush=True)
        return 0

    regioes = regioes_de_fala(origem)
    print(f"[2/4] fala: {len(regioes)} trechos detectados", flush=True)
    if not regioes:
        raise SystemExit("nao achei fala nenhuma no video.")

    trechos = montar_trechos(regioes, dur)
    mantido = sum(f - i for i, f in trechos)
    print(f"[3/4] corte: {len(trechos)} trechos · {mantido:.1f}s de {dur:.1f}s "
          f"({(1 - mantido / dur) * 100:.0f}% fora)", flush=True)

    niveis = [rms_db(origem, i, f) for i, f in trechos]
    validos = [n for n in niveis if n > -90]
    mediana = statistics.median(validos) if validos else 0.0

    ranges = []
    corrigidos = 0
    for (i, f), nivel in zip(trechos, niveis):
        ganho = 0.0
        if nivel > -90 and nivel < mediana - 1.0:
            ganho = round(min(GANHO_MAX, mediana - nivel), 1)
            corrigidos += 1
        ranges.append({"source": "a", "start": round(i, 3),
                       "end": round(f, 3), "gain_db": ganho})
    if corrigidos:
        print(f"      volume: {corrigidos} trecho(s) levantado(s) "
              f"(mediana {mediana:.1f} dB)", flush=True)

    edl = {"sources": {"a": "entrada.mp4"}, "ranges": ranges}
    (trabalho / "edl.json").write_text(json.dumps(edl, indent=2), encoding="utf-8")

    saida = trabalho / "corte.mp4"
    cmd = [sys.executable, str(EDVID / "render.py"), str(trabalho / "edl.json"),
           "-o", str(saida), "--no-subtitles"]
    if args.rascunho:
        cmd.append("--draft")
    print("[4/4] renderizando…", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not saida.exists():
        print(r.stdout[-1500:], file=sys.stderr)
        print(r.stderr[-1500:], file=sys.stderr)
        raise SystemExit("o render falhou.")

    final = duracao(saida)

    # Os intermediários do render (os segmentos extraídos e o master antes do
    # loudnorm) somam ~85 MB e não servem pra nada com o corte.mp4 pronto. Some
    # depois de o arquivo existir e ter duração — nunca antes.
    #
    # `transcripts/` FICA: é o cache que evita transcrever o mesmo vídeo de
    # novo quando se prova outro estilo de legenda, e custa 56 KB.
    for lixo in (trabalho / "clips_graded", trabalho / "clips_draft",
                 trabalho / "clips_preview"):
        shutil.rmtree(lixo, ignore_errors=True)
    (trabalho / "base.mp4").unlink(missing_ok=True)

    print(f"pronto: {saida}  ({final:.1f}s, era {dur:.1f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
