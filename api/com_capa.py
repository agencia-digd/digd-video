#!/usr/bin/env python3
"""Cola a capa por 1 segundo na frente do vídeo.

    python3 com_capa.py --dir /caminho/do/video --capa 02-capa.png

---------------------------------------------------------------------------
POR QUE ISSO EXISTE

O Instagram deixa escolher a capa de um Reel, mas quem chega pelo feed vê o
PRIMEIRO QUADRO em movimento, não a capa escolhida. Um segundo da capa na
frente resolve: o primeiro quadro passa a ser a capa, e quem para pra ler já
leu a frase antes do vídeo começar.

O que não é óbvio e quebra em silêncio:

- O trecho da capa precisa de ÁUDIO. Concatenar um pedaço mudo com um pedaço
  com som produz um arquivo onde o áudio começa fora de hora, ou some — cada
  ferramenta lida de um jeito, nenhuma reclama.
- Os dois pedaços precisam do MESMO tamanho, mesmo fps e mesmo formato de
  pixel, senão o concat aceita e entrega um vídeo que trava na emenda.

Por isso a capa é reescalada pro tamanho exato do vídeo e ganha silêncio na
mesma taxa do áudio dele.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SEGUNDOS = 1.0


def sonda(v: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_entries", "format=duration", str(v)],
        capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout or "{}")
    v_st = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    a_st = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), {})
    fps = v_st.get("r_frame_rate", "30/1")
    num, _, den = fps.partition("/")
    return {
        "w": int(v_st.get("width", 1080)),
        "h": int(v_st.get("height", 1920)),
        "fps": round(float(num) / float(den or 1)) or 30,
        "taxa": int(a_st.get("sample_rate", 48000)),
        "canais": int(a_st.get("channels", 2)),
        "dur": float(d.get("format", {}).get("duration", 0) or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--capa", required=True)
    ap.add_argument("--video", default=None,
                    help="qual final usar; padrão é o mais recente")
    args = ap.parse_args()
    d = args.dir

    capa = d / "capas" / args.capa
    if not capa.exists():
        raise SystemExit(f"não achei a capa {args.capa}.")

    if args.video:
        video = d / args.video
    else:
        # SÓ os renders de estilo servem de origem. `final-com-capa.mp4` e
        # `final-instagram.mp4` são derivados deste passo — usar um deles cola
        # uma SEGUNDA capa em cima da primeira, e o vídeo cresce 1 segundo a
        # cada vez sem ninguém notar, porque tudo "funciona".
        DERIVADOS = {"final-com-capa.mp4", "final-instagram.mp4"}
        finais = sorted((p for p in d.glob("final-*.mp4")
                         if p.name not in DERIVADOS and not p.name.endswith(".tmp.mp4")),
                        key=lambda p: p.stat().st_mtime)
        video = finais[-1] if finais else (d / "corte.mp4")
    if not video.exists():
        raise SystemExit("não achei o vídeo final.")

    m = sonda(video)
    print(f"[1/2] {video.name}: {m['w']}x{m['h']} · {m['fps']}fps · {m['dur']:.1f}s", flush=True)

    saida = d / "final-com-capa.mp4"
    tmp = d / "final-com-capa.tmp.mp4"

    # Um filtro só, sem arquivo intermediário: a capa vira um clipe de 1s do
    # tamanho exato do vídeo, com silêncio na mesma taxa, e concat junta os dois.
    # A CAPA CABE NO QUADRADO DO MEIO — e por construção, não por pedido.
    #
    # No perfil, o Instagram corta o Reel num quadrado central. A capa nasce
    # 9:16, então ao ser cortada perdia a primeira linha e o rodapé: sobrou
    # "LEU MEU E-MAIL" começando pela metade. Pedir área segura ao gerador
    # ajudou e não bastou — desenho generativo não obedece régua.
    #
    # Aqui ela é encolhida pra caber num quadrado de lado igual à largura, no
    # centro do quadro, e as faixas de cima e de baixo recebem o creme do papel
    # dela. O que o grid mostra passa a ser a capa inteira.
    lado = m["w"]
    borda = (m["h"] - lado) // 2
    filtro = (
        f"[0:v]scale={lado}:{lado}:force_original_aspect_ratio=decrease,"
        f"pad={m['w']}:{m['h']}:(ow-iw)/2:{borda}:color=0xF2EDE3,"
        f"setsar=1,fps={m['fps']},format=yuv420p[capa];"
        f"[1:v]scale={m['w']}:{m['h']},setsar=1,fps={m['fps']},format=yuv420p[v];"
        f"[capa][2:a][v][1:a]concat=n=2:v=1:a=1[vv][aa]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-t", str(SEGUNDOS), "-i", str(capa),
        "-i", str(video),
        "-f", "lavfi", "-t", str(SEGUNDOS),
        "-i", f"anullsrc=channel_layout={'stereo' if m['canais'] > 1 else 'mono'}:sample_rate={m['taxa']}",
        "-filter_complex", filtro,
        "-map", "[vv]", "-map", "[aa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(tmp),
    ]
    print("[2/2] colando a capa na frente…", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise SystemExit("não consegui colar a capa: " + (r.stderr or "")[-300:])

    # Confere ANTES de publicar: um arquivo sem stream de vídeo já passou
    # adiante uma vez neste projeto e ninguém viu até o player abrir preto.
    novo = sonda(tmp)
    if novo["dur"] < m["dur"] + SEGUNDOS - 0.5 or not novo["w"]:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"o arquivo saiu errado: {novo['dur']:.1f}s "
                         f"(esperava ~{m['dur'] + SEGUNDOS:.1f}s)")
    tmp.replace(saida)
    print(f"pronto: {saida.name} · {novo['dur']:.1f}s (era {m['dur']:.1f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
