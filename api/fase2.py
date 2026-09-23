#!/usr/bin/env python3
"""Fase 2: legenda, zoom, headline e trilha em cima do corte da Fase 1.

    python3 fase2.py --dir /caminho/do/video --legenda karaoke --headline card \
                     --linhas "PRIMEIRA LINHA" "SEGUNDA" --zoom-cortes --trilha warm

Entra o `corte.mp4` que a Fase 1 produziu, sai o `final.mp4` legendado.

---------------------------------------------------------------------------
POR QUE ASSIM

A regra dura do edvid é que a Fase 2 é **Remotion, nunca texto queimado com
ffmpeg**. Concordo e mantive: legenda queimada não se corrige depois e sai
serrilhada no vertical. Aqui o vídeo entra como camada e o texto é desenhado
por cima, em vetor.

E a Fase 2 escreve **um arquivo só**: o `edit-data.json`. O `Main.tsx` do
template nunca se toca — é ele que sabe desenhar os dez estilos, e mexer ali
quebraria todos de uma vez.

DUAS DECISÕES QUE VALEM A LEITURA

1. A TRANSCRIÇÃO É DO CORTE, NÃO DO ORIGINAL. Parece detalhe e é o que faz a
   legenda bater. Transcrever o original e tentar remapear os tempos pelos
   cortes acumula erro a cada emenda; no fim do vídeo a palavra aparece meio
   segundo depois da boca. Transcrever o `corte.mp4` custa uma passada a mais
   e acerta de graça.

2. SEM CHAVE DE API. O WhisperX roda local, no venv do edvid. Isso é o que
   permite o mesmo pipeline rodar em qualquer máquina sem assinar mais nada.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import config

EDVID = config.EDVID_HELPERS
REMOTION = config.REMOTION
PY_VENV = config.PY_TRANSCRICAO

LEGENDAS = ("karaoke", "stacked", "scatter", "simples", "serifada", "classica")
HEADLINES = ("outline", "card", "realce", "misto")
TRILHAS = ("tense", "punch", "warm", "cta", "dark", "tech")


def rodar(cmd: list[str], erro: str, minutos: int = 40, cwd: Path | None = None) -> str:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       timeout=minutos * 60, cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        cauda = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        raise SystemExit(f"{erro}: {cauda[-1][:240] if cauda else 'sem saída'}")
    return r.stdout


def conferir(v: Path, o_que: str) -> float:
    """Devolve a duração — e explode se o arquivo não presta.

    Existe porque um render do Remotion saiu com código 0 e um mp4 de 32 MB
    SEM STREAM NENHUM. O passo seguinte engasgou, meu código tratou como
    "tudo bem" e seguiu; a falha só apareceu no fim, como um ValueError sem
    sentido. Código de saída zero não prova que o vídeo presta: quem prova é
    olhar o arquivo.
    """
    if not v.exists() or v.stat().st_size < 10_000:
        raise SystemExit(f"{o_que}: o arquivo não saiu (ou saiu vazio).")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-show_entries", "stream=codec_type", "-of", "default=nw=1:nk=1", str(v)],
        capture_output=True, text=True)
    linhas = [x.strip() for x in r.stdout.splitlines() if x.strip()]
    if "video" not in linhas:
        raise SystemExit(f"{o_que}: o arquivo saiu corrompido (sem faixa de vídeo).")
    try:
        d = float(linhas[-1])
    except ValueError:
        raise SystemExit(f"{o_que}: o arquivo saiu corrompido (duração ilegível).")
    if d < 1.0:
        raise SystemExit(f"{o_que}: o vídeo saiu com {d:.1f}s — não terminou de escrever.")
    return d


def duracao(v: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(v)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def fps_de(v: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=r_frame_rate",
                        "-of", "default=nw=1:nk=1", str(v)],
                       capture_output=True, text=True, check=True)
    try:
        num, den = r.stdout.strip().split("/")
        return max(1, round(float(num) / float(den)))
    except Exception:  # noqa: BLE001
        return 30


def _legenda(base: dict, estilo: str, escala: float, subir: float = 0.0) -> dict:
    """Aplica tamanho e altura no botão que o ESTILO ESCOLHIDO realmente lê.

    Cada estilo do template tem o seu, e mandar o errado não dá erro nenhum —
    a legenda simplesmente sai do mesmo lugar de sempre e a pessoa acha que o
    controle está quebrado:

        TAMANHO
        stacked          -> fontScale        (base 0.8)
        scatter          -> scatterFontSize  (base 58 px)
        karaoke e demais -> fontSize         (o do próprio edit-data)

        ALTURA (`subir` = fração da tela pra cima, 0.10 = 10% mais alto)
        scatter          -> scatterOffsetY   (base 0.72 do centro do bloco)
        stacked          -> stackedOffsetY   (base 0.156 abaixo do centro)
        karaoke e demais -> paddingBottom    (pixels desde o pé do quadro)

    Os três estáticos (simples, serifada, clássica) não têm botão de altura no
    motor — são fixos em 430px por decisão de design de lá. Subir neles pediria
    mexer no template, não é ajuste de parâmetro.
    """
    c = {**base, "enabled": True, "style": estilo}
    if estilo == "stacked":
        c["fontScale"] = round(0.8 * escala, 3)
        if subir:
            c["stackedOffsetY"] = round(max(-0.42, 0.156 - subir), 4)
    elif estilo == "scatter":
        c["scatterFontSize"] = round(58 * escala)
        if subir:
            # 0.72 e o centro do bloco no terco de baixo. Chao em 0.15
            # porque acima disso a legenda sai pela borda de cima do quadro.
            c["scatterOffsetY"] = round(max(0.15, 0.72 - subir), 4)
    else:
        c["fontSize"] = round(base.get("fontSize", 61) * escala)
        if subir:
            # 1920 de altura: cada 0.01 de fração são 19 px de pé.
            c["paddingBottom"] = round(base.get("paddingBottom", 300) + subir * 1920)
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True, help="pasta do vídeo (tem corte.mp4)")
    ap.add_argument("--legenda", default="karaoke", choices=LEGENDAS)
    ap.add_argument("--headline", default=None, choices=HEADLINES)
    ap.add_argument("--linhas", nargs="*", default=[], help="texto da headline")
    ap.add_argument("--zoom-cortes", action="store_true")
    ap.add_argument("--zoom-auto", action="store_true")
    ap.add_argument("--rosto", action="store_true", help="câmera seguindo o rosto")
    ap.add_argument("--flash", action="store_true",
                    help="clarão branco na emenda entre tomadas")
    ap.add_argument("--flash-forca", type=float, default=0.55,
                    help="0 a 1 — acima de 0,7 vira estroboscópio")
    ap.add_argument("--trilha", default=None, choices=TRILHAS)
    ap.add_argument("--idioma", default=config.IDIOMA)
    ap.add_argument("--fonte-escala", type=float, default=1.0,
                    help="tamanho da legenda: 1.0 é o padrão, 1.4 aumenta 40%%")
    ap.add_argument("--fechamento", default=None,
                    help='a palavra do card final (ex: "QUERO")')
    ap.add_argument("--fechamento-antes", default="digita")
    ap.add_argument("--fechamento-depois", default="aqui embaixo")
    ap.add_argument("--fechamento-seg", type=float, default=3.0)
    ap.add_argument("--tela-dividida", type=Path, default=None,
                    help="JSON com as imagens da tela dividida (ver split.json)")
    ap.add_argument("--legenda-subir", type=float, default=0.0,
                    help="sobe a legenda em fração da tela (0.10 = 10%% mais alto)")
    ap.add_argument("--headline-escala", type=float, default=None,
                    help="multiplica o tamanho da headline (1.0 = padrão do estilo)")
    ap.add_argument("--headline-max-px", type=int, default=None,
                    help="teto do ajuste automático da headline (maior = mais alta)")
    ap.add_argument("--headline-largura", type=int, default=None,
                    help="largura que a headline pode ocupar (maior = mais alta)")
    args = ap.parse_args()

    d = args.dir
    corte = d / "corte.mp4"
    if not corte.exists():
        raise SystemExit("não achei o corte.mp4 — a Fase 1 precisa rodar antes.")

    if not (REMOTION / "node_modules").is_dir():
        raise SystemExit(f"o template do Remotion não está instalado em {REMOTION} "
                         "(falta node_modules). Rode scripts/instalar-edvid.sh.")
    trabalho = d / "fase2"
    if trabalho.exists():
        shutil.rmtree(trabalho)
    shutil.copytree(REMOTION, trabalho, symlinks=True,
                    ignore=shutil.ignore_patterns("out", ".git"))
    publico = trabalho / "public"
    publico.mkdir(exist_ok=True)

    print("[1/5] transcrevendo o corte (palavra por palavra)…", flush=True)
    # O transcribe.py do edvid guarda o resultado e pula quando o arquivo ja
    # existe. Isso e otimo enquanto o corte e o mesmo — e mentira quando ele
    # muda: as legendas saem com os tempos do corte ANTERIOR, cada palavra
    # aparecendo na hora errada ("a legenda esta fora de ordem do tempo") —
    # foi o que apareceu depois de refazer o corte quatro vezes seguidas.
    #
    # Cache que nao sabe do que depende nao e cache, e resposta velha. Aqui a
    # dependencia e o corte.mp4: se ele e mais novo, a transcricao morre.
    velhas = [t for t in (d / "transcripts").glob("*.json")
              if (d / "transcripts").exists()
              and t.stat().st_mtime < corte.stat().st_mtime]
    for t in velhas:
        print(f"      transcrição de {t.name} é anterior ao corte — refazendo", flush=True)
        t.unlink()
    rodar([PY_VENV, EDVID / "transcribe.py", corte, "--edit-dir", d,
           "--language", args.idioma],
          "a transcrição falhou", minutos=60)

    transcricao = next((p for p in [d / "transcripts" / "cut.json",
                                    d / "transcripts" / "corte.json"] if p.exists()), None)
    if transcricao is None:
        achados = sorted((d / "transcripts").glob("*.json")) if (d / "transcripts").exists() else []
        if not achados:
            raise SystemExit("a transcrição não gerou arquivo.")
        transcricao = achados[0]

    print("[2/5] montando as legendas…", flush=True)
    rodar([sys.executable, EDVID / "captions_for_remotion.py",
           "--transcript", transcricao, "-o", publico / "captions.json"],
          "não consegui montar as legendas")

    palavras = json.loads((publico / "captions.json").read_text(encoding="utf-8"))
    print(f"      {len(palavras)} palavras legendadas", flush=True)

    if args.fechamento:
        # A legenda cala durante o card de fechamento. Os dois dizem a mesma
        # coisa ao mesmo tempo, em lugares diferentes da tela, e o olho não
        # sabe qual ler — some a força dos dois. O card ganha porque é ele que
        # tem a palavra que a pessoa vai digitar.
        # -1s de folga: o disperso segura a última frase por um segundo inteiro
        # depois da última palavra (ScatterCaptions: endMs + fps). Cortar na
        # hora exata do card deixa a frase vazando por trás dele — foi o
        # "então" fantasma atrás do card.
        FOLGA_SUMICO = 1.6   # 1s de permanência + o fade de saída (8 frames)
        corta_ms = (duracao(corte) - args.fechamento_seg - FOLGA_SUMICO) * 1000
        antes = len(palavras)
        # Corta pelo FIM, não pelo início: palavra que começou antes e termina
        # dentro do card continua na tela e vaza por trás dele. Foi o que
        # aconteceu com um "então" fantasma atrás da palavra final.
        palavras = [c for c in palavras
                    if float(c.get("endMs", c.get("startMs", 0))) <= corta_ms]
        (publico / "captions.json").write_text(
            json.dumps(palavras, ensure_ascii=False), encoding="utf-8")
        if antes != len(palavras):
            print(f"      {antes - len(palavras)} palavra(s) caladas no fechamento",
                  flush=True)

    if args.trilha:
        print("[3/5] escolhendo a trilha…", flush=True)
        try:
            rodar([sys.executable, EDVID / "pick_bed.py", "--mood", args.trilha,
                   "-o", publico / "trilha.mp3"], "trilha")
        except SystemExit as e:
            print(f"      sem trilha: {e}", flush=True)   # trilha não bloqueia o vídeo
            args.trilha = None
    else:
        print("[3/5] sem trilha", flush=True)

    dur = duracao(corte)
    fps = fps_de(corte)
    dados = json.loads((publico / "edit-data.json").read_text(encoding="utf-8"))
    dados.update({
        "durationSec": round(dur, 3),
        "fps": fps,
        "camera": {**dados.get("camera", {}),
                   "enabled": bool(args.zoom_cortes or args.zoom_auto or args.rosto),
                   "zoomCuts": bool(args.zoom_cortes),
                   "pushIn": 0.04 if args.zoom_auto else 0.0,
                   "tracking": bool(args.rosto)},
        "captions": _legenda(dados.get("captions", {}), args.legenda, args.fonte_escala,
                          args.legenda_subir),
        "soundtrack": {**dados.get("soundtrack", {}), "enabled": bool(args.trilha),
                       "file": "trilha.mp3"},
    })
    if args.headline and args.linhas:
        # `text` em vez de `lines`: o motor SEMPRE requebra em duas linhas
        # equilibradas e ajusta o corpo pra caber. Mandando linha por linha, uma
        # frase longa vira duas linhas tortas e a fonte encolhe mais do que
        # precisava. Junta-se tudo e deixa ele quebrar.
        hook = {**dados.get("hook", {}), "enabled": True,
                "style": args.headline, "text": " ".join(args.linhas)}
        hook.pop("lines", None)
        if args.headline_escala and not args.headline_max_px:
            # O teto de cada estilo vive em HL_STYLES no Main.tsx do motor. A
            # escala anda em cima dele, pra "maior" querer dizer a mesma coisa
            # em todos os estilos. Se lá mudar, muda aqui — por isso o teto
            # aparece escrito, e não adivinhado.
            TETO = {"outline": 51, "card": 46, "realce": 48, "misto": 55}
            base = TETO.get(args.headline, 51)
            args.headline_max_px = max(24, min(140, round(base * args.headline_escala)))
            print(f"      headline: teto {base}px × {args.headline_escala} = "
                  f"{args.headline_max_px}px", flush=True)
        if args.headline_max_px:
            hook["maxFontPx"] = args.headline_max_px
            hook.pop("fontSizePx", None)
        if args.headline_largura:
            hook["safeWidth"] = args.headline_largura
        dados["hook"] = hook
    else:
        dados["hook"] = {**dados.get("hook", {}), "enabled": False}
    if args.tela_dividida and args.tela_dividida.exists():
        # A arte entra numa faixa e a cabeça dela fica na outra. Os arquivos
        # precisam estar em public/ com o nome que o edit-data cita — o motor
        # resolve por staticFile(), e caminho de fora dali vira imagem
        # quebrada sem erro nenhum no log.
        cfg = json.loads(args.tela_dividida.read_text(encoding="utf-8"))
        itens = []
        for it in cfg.get("itens", []):
            origem = Path(it["arquivo"])
            if not origem.is_absolute():
                origem = args.tela_dividida.parent / origem
            if not origem.exists():
                raise SystemExit(f"a imagem da tela dividida sumiu: {origem}")
            destino = publico / origem.name
            destino.write_bytes(origem.read_bytes())
            itens.append({"src": origem.name,
                          "start": float(it["inicio"]), "end": float(it["fim"]),
                          "fit": it.get("encaixe", "cover"),
                          "bandH": int(it.get("faixa", 750)),
                          "layout": it.get("posicao", "top")})
        dados["splitInserts"] = itens
        # O enquadramento pina o ROSTO e nao e universal: cada pessoa filma de
        # um jeito. Quem mediu o quadro manda os numeros aqui.
        if cfg.get("enquadramento"):
            dados["splitLayout"] = cfg["enquadramento"]
        print(f"      tela dividida: {len(itens)} imagem(ns)", flush=True)

    if args.flash:
        # As posições vêm do jcut_timeline que o render.py grava no EDL — são as
        # posições REAIS na saída. Somar as durações das ranges daria errado,
        # porque o J-cut encavala as emendas e desloca tudo.
        #
        # O primeiro corte (0.0s) fica de fora: clarão no frame zero não lê como
        # transição, lê como defeito de arquivo.
        try:
            trilha_jcut = json.loads(
                (d / "edl.json").read_text(encoding="utf-8")).get("jcut_timeline", [])
        except (OSError, json.JSONDecodeError):
            trilha_jcut = []
        cortes = [round(float(x["video_start_in_output"]), 3) for x in trilha_jcut
                  if float(x.get("video_start_in_output", 0)) > 0.15]
        dados["transitions"] = [{"at": t, "intensity": args.flash_forca} for t in cortes]
        print(f"      flash em {len(cortes)} emenda(s)", flush=True)
    else:
        dados["transitions"] = []

    if args.fechamento:
        # O card de fim mora no CustomGraphics.tsx — o template do edvid só tem
        # headline no começo; o card entra pelo patch em edvid-extras/. Continua
        # guiado por dados: aqui só se escreve o que ele vai ler.
        dados["fechamento"] = {
            "enabled": True,
            "palavra": args.fechamento,
            "antes": args.fechamento_antes,
            "depois": args.fechamento_depois,
            "duracaoSec": args.fechamento_seg,
        }
    else:
        dados["fechamento"] = {"enabled": False, "palavra": ""}

    (publico / "edit-data.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    shutil.copy(corte, publico / "cut.mp4")

    print(f"[4/5] renderizando {dur:.0f}s a {fps}fps — a parte demorada…", flush=True)
    final = d / "final.mp4"
    bruto = d / "render.mp4"       # o caro; só vira final.mp4 depois de conferido
    # cwd=trabalho: o Remotion resolve src/index.ts e public/ a partir do
    # diretório dele. Rodando de fora, o npx nem acha o pacote instalado.
    rodar(["npx", "--no-install", "remotion", "render", "src/index.ts", "Reels",
           str(bruto.resolve()), "--log=error"],
          "o render do Remotion falhou", minutos=90, cwd=trabalho)

    dur_render = conferir(bruto, "o render")
    print(f"      render ok: {dur_render:.1f}s", flush=True)

    print("[5/5] fechando pro social (1080×1920)…", flush=True)
    social = bruto.parent / "final-social.mp4"
    try:
        rodar([sys.executable, EDVID / "encode_social.py", bruto], "encode social")
        conferir(social, "o encode social")
        shutil.move(str(social), str(final))
        bruto.unlink(missing_ok=True)
    except SystemExit as e:
        # O encode é acabamento. Falhou, entrega o render, que já foi conferido.
        print(f"      sem o acabamento social ({e}) — entrego o render", flush=True)
        social.unlink(missing_ok=True)
        bruto.replace(final)

    dur_final = conferir(final, "o resultado")

    # A cópia do template do Remotion pesa ~300 MB por causa do node_modules, e
    # não serve pra nada depois que o vídeo saiu — ela é recriada em segundos no
    # próximo render. Dez vídeos guardando isso seriam 3 GB de node_modules
    # repetidos; numa máquina comum vira problema antes do décimo.
    #
    # Só limpa DEPOIS de conferir o resultado: se o render falhou, a pasta é a
    # única prova do que aconteceu.
    try:
        shutil.rmtree(trabalho)
    except OSError as e:
        print(f"      (não consegui limpar a pasta de trabalho: {e})", flush=True)

    print(f"pronto: {final}  ({dur_final:.1f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
