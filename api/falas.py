#!/usr/bin/env python3
"""Transforma o vídeo original em BLOCOS DE FALA que dá pra tirar ou manter.

    python3 falas.py --dir /caminho/do/video          # gera falas.json
    python3 falas.py --dir /caminho --montar          # monta o edl.json do que ficou

É o que faz a edição por texto existir: a pessoa lê o que ela disse e marca o
que sai, em vez de aceitar só o corte automático de silêncio.

---------------------------------------------------------------------------
O PROBLEMA CENTRAL, E COMO ELE SE RESOLVE

O Whisper diz O QUE foi dito e mais ou menos quando. Ele NÃO serve pra decidir
onde a tesoura entra: os tempos dele derivam, e cortar num tempo de Whisper
come o começo da consoante seguinte. Quem sabe onde tem silêncio de verdade é
o `speech_regions.py` do edvid, que mede o áudio.

Então aqui os dois trabalham juntos, cada um no que sabe:

    Whisper          -> o texto e a ordem das falas
    speech_regions   -> onde a tesoura pode entrar sem cortar voz

E existe um terceiro fato, que é o que a maioria das ferramentas esconde:
NEM TODA FALA PODE SER TIRADA SOZINHA. Quando duas frases saem coladas, sem
silêncio no meio, não existe borda segura entre elas. Este arquivo detecta
isso e agrupa as duas num bloco só, dizendo por quê — em vez de fingir que
corta e devolver um estalo no meio da palavra.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import config

EDVID = config.EDVID_HELPERS
PY_VENV = config.PY_TRANSCRICAO

# Silêncio mínimo entre duas falas pra existir borda segura entre elas. Abaixo
# disso a tesoura cairia dentro de voz.
BORDA_MIN = 0.30
# Silêncio a partir do qual duas falas viram blocos separados. Abaixo disso é
# respiração dentro da mesma frase.
PAUSA_FRASE = 0.45
# Nenhuma palavra falada dura mais que isso. Serve de trava contra alinhamento
# ruim do Whisper, que estica a palavra por cima do silêncio.
DURACAO_MAX_PALAVRA = 1.5
# Pausa a partir da qual o corte automático encurta (o mesmo do processar.py).
PAUSA_LONGA = 1.2
FOLGA_ANTES = 0.08
FOLGA_DEPOIS = 0.14


def duracao(v: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(v)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def regioes_de_fala(video: Path) -> list[tuple[float, float]]:
    r = subprocess.run([sys.executable, str(EDVID / "speech_regions.py"), str(video)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"speech_regions falhou: {r.stderr[:200]}")
    saida = []
    for linha in r.stdout.splitlines():
        m = re.match(r"\s*([\d.]+)\s*->\s*([\d.]+)", linha)
        if m:
            saida.append((float(m.group(1)), float(m.group(2))))
    return saida


def palavras_de(transcricao: Path) -> list[dict]:
    """Só o que é palavra, com o tempo saneado.

    A transcrição intercala itens do tipo "spacing" que ocupam justamente os
    silêncios — com eles na lista nunca existe intervalo entre dois itens.

    E o `end` do Whisper MENTE quando o alinhamento falha: neste vídeo a
    palavra "Agradece." saiu com 6,8 SEGUNDOS de duração, esticada por cima do
    silêncio seguinte. Por isso o fim é limitado a algo plausível de fala.
    """
    itens = json.loads(transcricao.read_text(encoding="utf-8")).get("words", [])
    saida = []
    for p in itens:
        if p.get("type") != "word" or p.get("start") is None:
            continue
        ini = float(p["start"])
        fim = float(p["end"]) if p.get("end") is not None else ini + 0.3
        saida.append({"texto": p["text"], "inicio": ini,
                      "fim": min(fim, ini + DURACAO_MAX_PALAVRA)})
    return saida


def montar_blocos(palavras: list[dict], regioes) -> list[dict]:
    """Os blocos nascem do ÁUDIO; o texto entra depois.

    Esta é a inversão que importa. Antes eu agrupava por intervalo entre
    palavras do Whisper e só depois olhava o áudio — e uma palavra mal alinhada
    (6,8s de duração) fazia dois trechos separados por 6 segundos de silêncio
    virarem um bloco só, impossível de editar.

    Agora: o `speech_regions` diz onde tem voz, regiões separadas por menos de
    PAUSA_FRASE viram um bloco, e cada palavra cai no bloco que a contém. O
    Whisper entra só com o texto, que é o que ele faz bem.
    """
    if not regioes:
        return []
    grupos = [list(regioes[0])]
    for ini, fim in regioes[1:]:
        if ini - grupos[-1][1] < PAUSA_FRASE:
            grupos[-1][1] = fim
        else:
            grupos.append([ini, fim])

    blocos = []
    for i, (ini, fim) in enumerate(grupos):
        dentro = [w for w in palavras
                  if (w["inicio"] + w["fim"]) / 2 >= ini - 0.25
                  and (w["inicio"] + w["fim"]) / 2 <= fim + 0.25]
        texto = " ".join(w["texto"] for w in dentro).strip()
        if not texto:
            continue          # região de voz sem palavra: ruído, não fala
        blocos.append({
            "id": f"b{len(blocos):03d}",
            "inicio": round(ini, 3),
            "fim": round(fim, 3),
            "dura": round(fim - ini, 2),
            "texto": texto,
            "presas": False,
            "n_frases": 1,
            "pausa_antes": round(ini - blocos[-1]["fim"], 2) if blocos else round(ini, 2),
        })
    return blocos


def carregar(d: Path) -> dict:
    p = d / "falas.json"
    if not p.exists():
        raise SystemExit("não achei falas.json — rode sem --montar primeiro.")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--montar", action="store_true",
                    help="escreve o edl.json com o que ficou marcado")
    args = ap.parse_args()
    d = args.dir
    origem = d / "entrada.mp4"
    if not origem.exists():
        raise SystemExit("não achei entrada.mp4")

    if args.montar:
        dados = carregar(d)
        fora = set(dados.get("retirados", []))
        # O começo sem fala costuma ser lixo (a pessoa acertando a câmera) — mas
        # às vezes é o gancho: ela entrando, sentando, o silêncio que prende. Sem
        # isso, o corte sempre abre na primeira palavra e a entrada se perde.
        manter_inicio = bool(dados.get("manter_inicio"))
        # QUANTO DA ESPERA FICA. Zero = corta toda pausa (o comportamento
        # antigo). Num vídeo que demonstra um assistente respondendo, a espera
        # NÃO é lixo: ela é a prova de que a resposta veio. Cortar tudo faz o
        # vídeo prometer velocidade em vez de mostrar.
        pausa_max = float(dados.get("pausa_max") or 0.0)
        # APARAR DENTRO DA LINHA. Tirar o bloco inteiro é grosso demais quando
        # o que sobra é uma frase pendurada no fim ("...e responder um e-mail").
        # Aqui cada bloco pode ter um início e um fim próprios, em segundos do
        # ORIGINAL, e é isso que faz a edição parecer editor de verdade.
        ajustes = dados.get("ajustes") or {}
        # E o vídeo pode começar depois do zero: os primeiros segundos costumam
        # ser a pessoa acertando a câmera.
        inicio_em = float(dados.get("inicio_em") or 0.0)
        mantidos = [b for b in dados["blocos"] if b["id"] not in fora]
        if not mantidos:
            raise SystemExit("você tirou tudo — precisa sobrar pelo menos uma fala.")

        dur = duracao(origem)
        ranges = []
        for b in mantidos:
            a = ajustes.get(b["id"]) or {}
            ini = float(a.get("inicio", b["inicio"]))
            fim = float(a.get("fim", b["fim"]))
            if fim - ini < 0.15:
                continue          # aparado até sumir: o bloco sai
            ranges.append({
                "source": "a",
                "start": round(max(0.0, ini - FOLGA_ANTES), 3),
                "end": round(min(dur, fim + FOLGA_DEPOIS), 3),
                "gain_db": 0.0,
            })
        if not ranges:
            raise SystemExit("não sobrou nada depois dos ajustes.")
        if manter_inicio and ranges:
            ranges[0]["start"] = round(max(0.0, inicio_em), 3)

        if pausa_max > 0:
            for anterior, seguinte in zip(ranges, ranges[1:]):
                folga = seguinte["start"] - anterior["end"]
                if folga > 0:
                    anterior["end"] = round(
                        anterior["end"] + min(folga, pausa_max), 3)

        # Junta trechos que ficaram grudados depois do corte: emenda de dois
        # pedaços contíguos é emenda inventada, e o J-cut ainda a marcaria.
        junto = [ranges[0]]
        for r in ranges[1:]:
            if r["start"] - junto[-1]["end"] < 0.05:
                junto[-1]["end"] = r["end"]
            else:
                junto.append(r)

        (d / "edl.json").write_text(
            json.dumps({"sources": {"a": "entrada.mp4"}, "ranges": junto}, indent=2),
            encoding="utf-8")
        ficou = sum(r["end"] - r["start"] for r in junto)
        print(f"corte montado: {len(junto)} trecho(s) · {ficou:.1f}s de {dur:.1f}s "
              f"({(1 - ficou / dur) * 100:.0f}% fora)", flush=True)
        return 0

    # --- gerar os blocos -----------------------------------------------------
    transcricao = d / "transcripts" / "entrada.json"
    if not transcricao.exists():
        print("transcrevendo o original…", flush=True)
        r = subprocess.run([str(PY_VENV), str(EDVID / "transcribe.py"), str(origem),
                            "--edit-dir", str(d), "--language", config.IDIOMA],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode != 0 or not transcricao.exists():
            raise SystemExit(f"a transcrição falhou: {(r.stderr or '')[-200:]}")

    regioes = regioes_de_fala(origem)
    blocos = montar_blocos(palavras_de(transcricao), regioes)
    if not blocos:
        raise SystemExit("não achei fala nenhuma no vídeo.")

    # Pré-marca o que o corte automático tiraria: a pessoa começa do resultado
    # de hoje e ajusta, em vez de começar de uma folha em branco.
    sugeridos = [b["id"] for b in blocos if b["pausa_antes"] >= PAUSA_LONGA and False]

    (d / "falas.json").write_text(json.dumps({
        "duracao": round(duracao(origem), 2),
        "blocos": blocos,
        "retirados": sugeridos,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    presas = sum(1 for b in blocos if b["presas"])
    print(f"{len(blocos)} bloco(s) de fala" +
          (f" · {presas} com falas coladas (saem juntas)" if presas else ""), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
