#!/usr/bin/env python3
"""Aplica o que ela marcou na linha do tempo do editor.

    python3 aplicar.py --dir /caminho/do/video

Lê o `preview_edits.json` que a tela do edvid escreve e transforma em `edl.json`.

---------------------------------------------------------------------------
AS DUAS COISAS QUE ELA FAZ NAQUELA TELA

1. ARRASTA A BORDA de um trecho. Isso já vem pronto: o `edl.ranges` do arquivo
   salvo é o corte inteiro, com os ajustes dela dentro.

2. ESCREVE UMA NOTA em cima de um pedaço. Aí está o que o editor do edvid não
   resolve sozinho — a nota é texto livre, e é o AGENTE que lê e entende. Uma
   nota dizendo "corta" sobre 40,2s a 41,8s quer dizer: tire este pedaço.

   Reconhecer isso aqui, no código, é melhor que pedir pra ela aprender uma
   sintaxe. Ela escreveu "corts" com erro de digitação e continua valendo.

O QUE NÃO SE ADIVINHA: nota que não é pedido de corte vira aviso na resposta,
nunca ação. Apagar um pedaço do vídeo dela porque um texto ambíguo pareceu uma
ordem é o tipo de erro que ninguém desfaz.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path

# "corta", "corts", "cortar", "tira", "tirar", "remove" — com ou sem acento,
# com ou sem erro de digitação no fim.
PEDE_CORTE = re.compile(r"^(cort|tir|remov|apag|sai|fora)", re.I)


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")


def e_corte(texto: str) -> bool:
    t = sem_acento((texto or "").strip().lower())
    return bool(t) and bool(PEDE_CORTE.match(t))


TRILHA = [[]]


def em_tempo_de_fonte(ranges: list[dict], ini: float, fim: float) -> list[tuple]:
    """Traduz um trecho marcado NA TELA para o tempo do vídeo original.

    -------------------------------------------------------------------------
    O ERRO QUE ISSO CONSERTA

    A tela toca o `corte.mp4` — o vídeo que já perdeu os silêncios. O relógio
    que ela vê corre nesse arquivo. A EDL, por baixo, fala em tempo do
    `entrada.mp4`. São dois relógios, e a diferença cresce a cada silêncio que
    saiu antes do ponto marcado.

    Eu usava o número da tela direto na EDL. Ela marcou a tomada repetida em
    22s e eu cortei os 22s do original, que é outra frase. Os três cortes dela
    caíram em três lugares aleatórios, e o sistema não tinha como perceber:
    números válidos, arquivo válido, resultado errado.

    O trecho marcado pode atravessar um silêncio já removido — por isso a volta
    é uma LISTA, não um par. Cada pedaço da EDL que a marcação encosta devolve
    a sua fatia, no tempo do original.
    A TABELA QUE FAZ ISSO SER EXATO

    O render grava `jcut_timeline` no proprio edl.json: onde cada pedaço começa
    no arquivo final e quanto dura ali. A tela lê essa tabela e desenha por ela.
    Eu somava as durações da EDL à mão — e a soma dá 54,2s onde o arquivo tem
    51,6s, porque o J-cut encavala as tomadas e cada emenda come alguns quadros.
    5% aos 30 segundos é uma palavra e meia de erro.

    Com a tabela não há aproximação: cada pedaço tem começo e duração medidos.
    -------------------------------------------------------------------------
    """
    fatias, acum = [], 0.0
    for i, r in enumerate(ranges):
        a, b = float(r["start"]), float(r["end"])
        dur = b - a
        if i < len(TRILHA[0]):
            # A posição EXATA deste pedaço na tela, escrita pelo render.
            j = TRILHA[0][i]
            tela_a = float(j["video_start_in_output"])
            tela_b = tela_a + float(j["video_duration"])
            escala = (tela_b - tela_a) / dur if dur > 0 else 1.0
        else:
            tela_a, tela_b, escala = acum, acum + dur, 1.0
        acum = tela_b
        corte_a, corte_b = max(ini, tela_a), min(fim, tela_b)
        if corte_b <= corte_a:
            continue
        fatias.append((a + (corte_a - tela_a) / escala,
                       a + (corte_b - tela_a) / escala))
    return fatias


def tirar(ranges: list[dict], ini: float, fim: float) -> list[dict]:
    """Remove [ini, fim] dos trechos, partindo o que for atravessado no meio."""
    saida = []
    for r in ranges:
        a, b = float(r["start"]), float(r["end"])
        if fim <= a or ini >= b:
            saida.append(r)                       # não encosta
            continue
        if ini > a:
            saida.append({**r, "start": a, "end": round(min(ini, b), 3)})
        if fim < b:
            saida.append({**r, "start": round(max(fim, a), 3), "end": b})
    return [r for r in saida if r["end"] - r["start"] > 0.15]


def o_que_sai(d: Path, antes: list[dict], depois: list[dict]) -> list[str]:
    """As FRASES que este corte remove — não os segundos.

    Nasceu de um erro que ninguém pegou olhando número: as marcações dela
    vinham no relógio do vídeo cortado e eram lidas no relógio do original.
    Tudo parecia certo — três marcações, três cortes, duração menor — e o
    vídeo saía picotado no meio de frases.

    Segundo confere com segundo. Frase é o que denuncia."""
    try:
        falas = json.loads((d / "falas.json").read_text(encoding="utf-8"))["blocos"]
    except (OSError, KeyError, json.JSONDecodeError):
        return []

    def cobre(t: float, faixas: list[dict]) -> bool:
        return any(float(r["start"]) <= t <= float(r["end"]) for r in faixas)

    saiu = []
    for b in falas:
        meio = (float(b["inicio"]) + float(b["fim"])) / 2
        if cobre(meio, antes) and not cobre(meio, depois):
            saiu.append(f'{b["inicio"]:.1f}s  "{b["texto"][:70]}"')
    return saiu


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    args = ap.parse_args()
    d = args.dir
    p = d / "preview_edits.json"
    if not p.exists():
        raise SystemExit("não achei edição salva no editor.")

    dados = json.loads(p.read_text(encoding="utf-8"))
    # O edl.json do disco e a fonte tanto dos trechos quanto da tabela de
    # posicoes. Leio uma vez so.
    try:
        dados_edl = json.loads((d / "edl.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        dados_edl = {}

    brutos = dados.get("edl", {}).get("ranges", [])
    if not brutos:
        # A tela só grava a EDL quando ela ARRASTA a borda de um trecho. Quando
        # ela apenas escreve notas — que é o caminho normal, e o que a tela
        # ensina a fazer — o arquivo salvo vem com `notes` e nada mais.
        #
        # Aqui isso virava "a edição salva não tem trecho nenhum", e ela ficou
        # olhando pra três cortes marcados na tela com o sistema dizendo que
        # não havia nada. A base certa, nesse caso, é o corte que já existe.
        brutos = dados_edl.get("ranges", [])
    ranges = [{"source": r.get("source", "a"),
               "start": round(float(r["start"]), 3),
               "end": round(float(r["end"]), 3),
               "gain_db": 0.0}
              for r in brutos]
    if not ranges:
        raise SystemExit("não achei o corte atual pra aplicar as marcações em cima.")

    ranges_antes = [dict(r) for r in ranges]
    TRILHA[0] = dados_edl.get("jcut_timeline") or []
    if len(TRILHA[0]) != len(ranges):
        # Sem a tabela (ou desencontrada dos trechos) a conta volta a ser soma
        # de duracoes, que erra. Melhor dizer isso alto do que cortar torto.
        print(f"AVISO: sem a tabela de posições ({len(TRILHA[0])} para "
              f"{len(ranges)} trechos) — as marcações podem sair alguns "
              f"décimos fora do lugar.", flush=True)
        TRILHA[0] = []
    antes = sum(r["end"] - r["start"] for r in ranges)
    cortadas, ignoradas = [], []
    for n in dados.get("notes", []):
        texto = str(n.get("text", ""))
        # `renderedStart/End` e a posicao no arquivo que esta tocando, que e o
        # que ela enxerga. `start/end` e a posicao na linha do tempo montada.
        # Quando os dois existem, o que manda e o do arquivo.
        try:
            ini = float(n.get("renderedStart", n["start"]))
            fim = float(n.get("renderedEnd", n["end"]))
        except (KeyError, TypeError, ValueError):
            continue
        if e_corte(texto):
            for a, b in em_tempo_de_fonte(ranges, ini, fim):
                ranges = tirar(ranges, a, b)
            cortadas.append((ini, fim, texto))
        else:
            ignoradas.append((ini, fim, texto))

    # Junta o que ficou colado depois de tirar: emenda entre dois pedaços
    # contíguos é emenda inventada, e o J-cut ainda a marcaria.
    ranges.sort(key=lambda r: r["start"])
    junto = [ranges[0]]
    for r in ranges[1:]:
        if r["start"] - junto[-1]["end"] < 0.05:
            junto[-1]["end"] = r["end"]
        else:
            junto.append(r)

    (d / "edl.json").write_text(
        json.dumps({"sources": {"a": "entrada.mp4"}, "ranges": junto}, indent=2),
        encoding="utf-8")
    # A edição foi consumida. Deixar o arquivo faria a tela seguir dizendo que
    # há alteração pendente depois de já ter sido aplicada.
    p.rename(d / "preview_edits.aplicado.json")

    depois = sum(r["end"] - r["start"] for r in junto)
    print(f"aplicado: {len(junto)} trecho(s) · {depois:.1f}s (era {antes:.1f}s)", flush=True)
    frases = o_que_sai(d, ranges_antes, junto)
    if frases:
        print("   falas que saem:", flush=True)
        for f in frases:
            print(f"      {f}", flush=True)
    else:
        print("   nenhuma fala inteira sai — só silêncio ou pedaço de fala.", flush=True)
    for ini, fim, t in cortadas:
        print(f"   cortei {ini:.1f}-{fim:.1f}s  (sua nota: {t!r})", flush=True)
    for ini, fim, t in ignoradas:
        print(f"   NÃO entendi como corte, deixei: {ini:.1f}-{fim:.1f}s {t!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
