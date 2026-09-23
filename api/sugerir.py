#!/usr/bin/env python3
"""A IA lê o que a pessoa falou e propõe o corte.

    python3 sugerir.py --dir /caminho/do/video

Escreve a sugestão dentro do `falas.json`: quais blocos sair, quanta espera
manter, e o PORQUÊ de cada retirada — que é o que a tela mostra pra ela
aprovar ou recusar com conhecimento de causa.

---------------------------------------------------------------------------
DUAS DECISÕES QUE VALEM A LEITURA

1. A IA PROPÕE, NUNCA APLICA. A saída dela vai pra tela como sugestão marcada,
   e o vídeo só é recortado quando a pessoa aprova. Um assistente que corta
   sozinho e avisa depois transforma cada erro dele em trabalho dela.

2. ELA SÓ MEXE NO QUE É TEXTO. Quais falas saem, e por quê. Não escolhe
   estilo, não decide tempo de espera técnico, não mexe em render. O que ela
   sabe fazer é ler e entender que "O app responde... Bom dia, tudo bem? Pode..."
   é uma tomada que não emendou — e isso nenhum detector de silêncio pega,
   porque tem voz ali.

A IA roda pelo Claude Code (`claude -p`) e é OPCIONAL. Sem ele instalado, este
script não falha: grava uma sugestão vazia dizendo que a IA está desligada, e o
corte automático de silêncio segue normalmente.
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

CLAUDE = config.CLAUDE_BIN
MODELO = config.IA_MODELO

INSTRUCAO = """Você é editor de vídeo curto. Abaixo está a transcrição de um vídeo,
quebrada em blocos de fala com id e duração.

Sua tarefa: dizer quais blocos DEVEM SAIR do corte final.

TIRE:
- tomada repetida ou que não emendou (a pessoa começa, se perde e recomeça)
- gaguejo, "é... é...", frase abandonada no meio
- fala que repete o que já foi dito logo antes, sem acrescentar

NÃO TIRE:
- o começo do vídeo, mesmo hesitante — é o gancho
- a chamada final (convite, pedido de comentário, "me chama")
- explicação que parece repetitiva mas fecha o raciocínio

Responda SÓ com um JSON, sem mais nada:
{"retirar": [{"id": "b007", "porque": "tomada repetida, ela recomeça em b010"}],
 "resumo": "uma frase sobre o que você fez"}

Se não houver nada pra tirar, devolva "retirar": [].
"""


def perguntar(blocos: list[dict]) -> dict:
    listagem = "\n".join(
        f'{b["id"]} ({b["dura"]:.1f}s): {b["texto"]}' for b in blocos)
    r = subprocess.run(
        [CLAUDE, "-p", f"{INSTRUCAO}\n\nBLOCOS:\n{listagem}", "--model", MODELO],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"a IA não respondeu: {(r.stderr or '')[-200:]}")
    bruto = (r.stdout or "").strip()
    # A resposta pode vir cercada de texto ou de cerca de código; pega o JSON.
    m = re.search(r"\{.*\}", bruto, re.S)
    if not m:
        raise SystemExit(f"a IA respondeu fora do formato: {bruto[:200]}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise SystemExit(f"não entendi a resposta da IA: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    args = ap.parse_args()
    p = args.dir / "falas.json"
    if not p.exists():
        raise SystemExit("não achei falas.json — prepare as falas primeiro.")

    dados = json.loads(p.read_text(encoding="utf-8"))
    blocos = dados["blocos"]
    validos = {b["id"] for b in blocos}

    if not config.ia_ok():
        # Sem IA não é erro: é a instalação mais simples. A pessoa marca o que
        # sai na tela, como faria se a IA não tivesse achado nada.
        resposta = {"retirar": [], "resumo": (
            "A IA de corte está desligada nesta instalação (Claude Code não "
            "encontrado). Tirei só os silêncios; marque você o que mais sai.")}
    else:
        resposta = perguntar(blocos)
    tirar = [x for x in resposta.get("retirar", [])
             if isinstance(x, dict) and x.get("id") in validos]

    # Trava: uma IA que resolve cortar quase tudo é uma IA que entendeu errado,
    # e a pessoa perderia tempo desfazendo. Acima de metade, não sugere nada e
    # diz por quê.
    if len(tirar) > len(blocos) / 2:
        dados["sugestao"] = {
            "retirar": [],
            "resumo": (f"A IA quis tirar {len(tirar)} de {len(blocos)} falas. "
                       "É demais pra confiar sem você olhar — não marquei nada."),
            "conferir": True,
        }
    else:
        dados["sugestao"] = {
            "retirar": tirar,
            "resumo": str(resposta.get("resumo", ""))[:300],
        }

    # A sugestão vira a marcação inicial. Ela ainda não foi aplicada em nada:
    # o vídeo só muda quando a pessoa aprovar.
    dados["retirados"] = [x["id"] for x in dados["sugestao"]["retirar"]]
    dados.setdefault("manter_inicio", True)
    dados.setdefault("pausa_max", 3.0)

    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"sugestão: tirar {len(dados['retirados'])} de {len(blocos)} falas", flush=True)
    for x in dados["sugestao"]["retirar"]:
        print(f"   {x['id']}: {x.get('porque', '')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
