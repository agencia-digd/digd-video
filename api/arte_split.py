#!/usr/bin/env python3
"""Gera as artes da tela dividida, no estilo de uma família já aprovada.

    python3 arte_split.py --dir /caminho/do/video --familia aquarela \
        --arte "5.1-11.7|uma xícara de café fumegando sobre a mesa" \
        --arte "19.1-28.3|um jardim fechado, sem sol, folhas murchas"

Cada `--arte` é `inicio-fim|o que desenhar`. O script gera, guarda em
`split/` e escreve o `split.json` que a Fase 2 lê.

---------------------------------------------------------------------------
A FAMÍLIA É UMA PASTA DE IMAGENS, NÃO UM PARÁGRAFO

Mesma lição das capas, um nível acima. Descrever o estilo em palavras —
"aquarela, laranja âmbar sobre azul-noite" — produz algo que atende à descrição
e não pertence à mesma série. Duas artes assim, lado a lado num carrossel de
sete dias, não parecem irmãs.

Então o estilo vive em `referencias/arte/<familia>/`, com algumas imagens
aprovadas dentro, e vai como referência visual em toda geração. Trocar o padrão
é trocar as imagens da pasta.

Uma família bem feita é um tratamento só — digamos aquarela e nanquim sobre
textura de papel — e cada vídeo da série muda o assunto e a cor dentro do MESMO
tratamento. É o que faz a série parecer série.

O desenho é feito pelo GERADOR DE IMAGEM externo (VIDEOS_GERADOR_IMAGEM, contrato
no README). Sem ele configurado, este script recusa com mensagem clara.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

import config

GERADOR = config.GERADOR_IMAGEM
REFS = config.REFERENCIAS_ARTE

# O que vale pra QUALQUER família. O estilo em si está nas imagens.
BASE = """Ilustração para a faixa superior de um vídeo vertical — formato horizontal largo,
composição centrada, com respiro nas bordas.

Copie fielmente a linguagem visual das IMAGENS DE REFERÊNCIA: a técnica, a textura, a
paleta e o clima delas. Elas são a série; esta arte é mais uma dela, não um estilo novo.

SEM TEXTO, sem letras, sem números, sem marca d'água, sem moldura. Nada de 3D, nada de
brilho digital, nada de vetor chapado."""


def familia(nome: str | None) -> tuple[str, list[Path]]:
    nome = (nome or "").strip() or _padrao()
    pasta = REFS / nome
    return nome, sorted(pasta.glob("*.png")) + sorted(pasta.glob("*.jpg"))


def _padrao() -> str:
    try:
        return (REFS / "padrao.txt").read_text(encoding="utf-8").strip() or "padrao"
    except OSError:
        return "padrao"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--familia", default=None)
    ap.add_argument("--arte", action="append", default=[],
                    help="inicio-fim|descrição; pode repetir")
    ap.add_argument("--faixa", type=int, default=750,
                    help="altura da faixa de arte, em pixels")
    ap.add_argument("--enquadramento", default=None,
                    help='JSON tipo {"top":{"zoom":1.0,"focusY":230}} — MEDIDO neste vídeo')
    ap.add_argument("--plano", type=Path, help="Plano validado pela fila; reutiliza imagens não marcadas para refazer")
    args = ap.parse_args()

    d = args.dir
    if not config.gerador_ok():
        raise SystemExit(config.motivo_sem_gerador())
    if not (d / "corte.mp4").exists():
        raise SystemExit("não achei o corte deste vídeo.")

    nome, refs = familia(args.familia)
    if not refs:
        raise SystemExit(f"a família '{nome}' não tem imagem nenhuma em {REFS / nome}. "
                         f"Sem referência, o estilo vira sorteio.")
    print(f"estilo: {nome} ({len(refs)} referência(s))", flush=True)

    destino = d / "split"
    destino.mkdir(exist_ok=True)
    plano_pedido = json.loads(args.plano.read_text(encoding="utf-8")) if args.plano else {}
    pedidos = plano_pedido.get("itens") if args.plano else [
        {"inicio": float(a.partition("|")[0].partition("-")[0]),
         "fim": float(a.partition("|")[0].partition("-")[2]),
         "descricao": a.partition("|")[2], "faixa": args.faixa, "posicao": "top"}
        for a in args.arte]
    itens = []
    for i, item in enumerate(pedidos, 1):
        if item.get("arquivo") and not item.get("refazer"):
            itens.append({k: v for k, v in item.items() if k != "refazer"})
            continue
        pedido = f'{item["inicio"]}-{item["fim"]}|{item.get("descricao", "")}'
        janela, _, descricao = pedido.partition("|")
        ini, _, fim = janela.partition("-")
        if not descricao.strip():
            raise SystemExit(f"faltou a descrição em: {pedido!r}")
        saida = destino / f"{i:02d}-{uuid.uuid4().hex}-arte.png"
        print(f"[{i}/{len(pedidos)}] {ini}s–{fim}s · {descricao.strip()[:60]}…", flush=True)
        r = subprocess.run(
            [str(GERADOR), f"{BASE}\n\nO que desenhar: {descricao.strip()}",
             str(saida), *[str(p) for p in refs]],
            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0 or not saida.exists():
            cauda = (r.stderr or r.stdout or "").strip().splitlines()[-2:]
            raise SystemExit(f"a arte {i} falhou: {' · '.join(cauda)}")
        itens.append({**{k: v for k, v in item.items() if k != "refazer"},
                      "arquivo": f"split/{saida.name}",
                      "inicio": float(ini), "fim": float(fim),
                      "faixa": item.get("faixa", args.faixa), "posicao": item.get("posicao", "top")})

    plano = {"_": f"Tela dividida gerada por arte_split.py · família {nome}",
             "familia": nome, "itens": itens}
    if "enquadramento" in plano_pedido:
        plano["enquadramento"] = plano_pedido["enquadramento"]
    elif (d / "split.json").exists():
        anterior = json.loads((d / "split.json").read_text(encoding="utf-8"))
        if "enquadramento" in anterior:
            plano["enquadramento"] = anterior["enquadramento"]
    if args.enquadramento:
        plano["enquadramento"] = json.loads(args.enquadramento)
    alvo = d / "split.json"
    if alvo.exists():
        # Guardo o anterior antes de trocar. Um "--arte teste" ja levou junto o
        # plano de quatro artes que estava aprovado — trabalho de meia hora que
        # so nao se perdeu porque havia copia em outro lugar.
        antigo = d / "split.anterior.json"
        antigo.write_text(alvo.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"      o plano anterior virou {antigo.name}", flush=True)
    temporario = d / "split.json.tmp"
    temporario.write_text(json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(alvo)
    print(f"pronto: {len(itens)} arte(s) · split.json escrito", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
