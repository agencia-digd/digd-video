#!/usr/bin/env python3
"""Gera a capa de um vídeo, no estilo de uma capa já aprovada.

    python3 capa.py --dir /caminho/do/video --frase "pedi pra minha IA|MINHA AGENDA|e ela até|RESPONDEU MEUS E-MAILS"

---------------------------------------------------------------------------
POR QUE A REFERÊNCIA É UMA IMAGEM E NÃO UM TEXTO

A primeira capa desenhada descrevia a pessoa do vídeo em palavras — cabelo,
óculos, roupa — e saiu outra pessoa, que atende à descrição e não é ela.
Descrição não identifica ninguém.

Então vão DUAS imagens de referência em toda geração:

  1. um quadro do vídeo, pra ser o rosto de verdade;
  2. uma capa já aprovada, pra ser o estilo.

As (2) vivem em referencias/<familia>.png e são trocadas pela tela. Podem ser
várias linguagens — uma barulhenta pra demonstração de produto, outra calma pra
bastidor e opinião. É por isso que a aba tem "usar como referência": o padrão da
casa é um arquivo, não um parágrafo neste script.

O desenho em si é feito por um GERADOR DE IMAGEM externo (VIDEOS_GERADOR_IMAGEM,
contrato no README). Sem ele configurado, este script recusa com mensagem clara
e o resto do editor segue funcionando.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import config

AQUI = Path(__file__).resolve().parent
GERADOR = config.GERADOR_IMAGEM
REFS = config.REFERENCIAS


def familia(nome: str | None) -> tuple[str, Path | None]:
    """Qual capa vai servir de estilo desta vez.

    São várias, não uma: linguagens diferentes servem a vídeos diferentes —
    uma barulhenta pra demonstração de produto, outra calma pra bastidor e
    opinião. Uma referência só obrigaria a escolher entre elas."""
    nome = (nome or "").strip() or _padrao()
    p = REFS / f"{nome}.png"
    return nome, (p if p.exists() else None)


def _padrao() -> str:
    try:
        return (REFS / "padrao.txt").read_text(encoding="utf-8").strip() or "colagem"
    except OSError:
        return "colagem"

# O estilo NÃO está descrito aqui — está na segunda imagem. Descrever em
# palavras foi o que produziu uma capa com outra pessoa; e descrever a
# construção travaria a casa numa linguagem só. Aqui fica o que vale para
# QUALQUER família: é a pessoa do vídeo na foto, e o texto tem hierarquia.
# QUADRADA, e não 9:16. A grade do perfil corta o Reel num quadrado; uma capa
# vertical só cabe inteira ali quando fica pequena — sobravam 236px de creme de
# cada lado. Quadrada, ela ocupa a grade toda E aparece grande no Reel.
ESTILO = """Capa QUADRADA 1:1 para Reel — proporção exata de quadrado, nem um pouco vertical. Copie fielmente a linguagem visual da SEGUNDA imagem de
referência — composição, tratamento, tipografia, paleta e clima. Ela é o padrão; não
invente um estilo novo.

A pessoa é a DA PRIMEIRA IMAGEM DE REFERÊNCIA. Mantenha o rosto como é: formato,
bochechas, sobrancelhas, cabelo, óculos e acessórios se houver, e a roupa que aparece no
quadro. Não afine o rosto, não mude o corpo, não idealize — é a mesma pessoa.

ÁREA SEGURA — isto é regra de composição, não sugestão:
No feed do Instagram esta capa é cortada num QUADRADO no meio. Tudo que importa
— cada linha de texto e o rosto — tem que caber no quadrado central, com
folga. As bordas de cima e de baixo levam só fundo, textura e enfeite: o que
cair lá some pra quem vê pelo perfil.

Sem gradiente colorido, sem 3D, sem brilho artificial no rosto."""


def texto(frase: str) -> str:
    """As linhas separadas por | viram a hierarquia da capa.

    Quatro linhas é o formato que funcionou: um sussurro à mão, a frase grande,
    uma ponte pequena e o remate grifado em amarelo — que é onde cai a parte
    que ninguém pediu."""
    linhas = [x.strip() for x in frase.split("|") if x.strip()]
    if not linhas:
        raise SystemExit("preciso da frase da capa.")
    papeis = [
        "pequeno, à mão, em rosa",
        "enorme, letra pesada condensada preta",
        "médio, preto",
        "grande, dentro de uma caixa amarela #FFD413 chapada e torta",
    ]
    corpo = "\n".join(f"- {papeis[min(i, 3)]}: '{ln}'" for i, ln in enumerate(linhas))
    assinatura = (f"\n\n'{config.ASSINATURA_CAPA}' pequeno e discreto, dentro da área segura."
                  if config.ASSINATURA_CAPA else "")
    return f"{ESTILO}{assinatura}\n\nTexto em português, atravessando o recorte:\n{corpo}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--frase", required=True)
    ap.add_argument("--segundo", type=float, default=None,
                    help="de que segundo do vídeo tirar o rosto")
    ap.add_argument("--familia", default=None,
                    help="qual capa serve de estilo (ex.: colagem, calma…)")
    args = ap.parse_args()
    d = args.dir
    if not config.gerador_ok():
        raise SystemExit(config.motivo_sem_gerador())

    video = next((v for v in [d / "final-scatter.mp4", d / "corte.mp4", d / "entrada.mp4"]
                  if v.exists()), None)
    if video is None:
        raise SystemExit("não achei vídeo nenhum nesta pasta.")

    capas = d / "capas"
    capas.mkdir(exist_ok=True)
    rosto = capas / ".rosto.png"

    # Meio do vídeo por padrão: começo e fim costumam ter card ou movimento.
    seg = args.segundo if args.segundo is not None else 0
    if not seg:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(video)],
                           capture_output=True, text=True)
        try:
            seg = float(r.stdout.strip()) * 0.55
        except ValueError:
            seg = 10.0

    print(f"[1/2] tirando o rosto de {video.name} aos {seg:.0f}s…", flush=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(seg), "-i", str(video),
                    "-frames:v", "1", str(rosto)], check=True, timeout=180)

    refs = [str(rosto)]
    nome, ref = familia(args.familia)
    if ref:
        refs.append(str(ref))
        print(f"      estilo: {nome}", flush=True)
    else:
        print(f"      AVISO: não achei a referência '{nome}' — o estilo vai "
              f"depender só do texto, e o texto não descreve ninguém.", flush=True)

    n = 1 + max([int(p.stem.split("-")[0]) for p in capas.glob("[0-9]*.png")] or [0])
    saida = capas / f"{n:02d}-capa.png"

    print(f"[2/2] gerando a capa (leva alguns minutos)…", flush=True)
    r = subprocess.run([str(GERADOR), texto(args.frase), str(saida), *refs],
                       capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not saida.exists():
        cauda = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        raise SystemExit("a geração da capa falhou: " + " · ".join(cauda))

    rosto.unlink(missing_ok=True)
    print(f"pronto: {saida}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
