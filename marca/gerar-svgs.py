"""Gera os SVGs da marca dig.D Vídeo. Ícone em coordenadas à mão; wordmark = glifos do DM Sans em curvas.
Uso: pip install fonttools && python gerar-svgs.py <pasta-de-saída>  (pede DM Sans variável em FONT)."""
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen

OUT = sys.argv[1]
AZUL, ROSA, AMARELO, TINTA, CREME = '#064794', '#EA2871', '#FFD413', '#15141B', '#F4F1E9'
FONT = '/usr/local/share/fonts/digd/DMSans.ttf'

def inst(w):
    return instancer.instantiateVariableFont(TTFont(FONT), {'wght': w, 'opsz': 40})
F800, F500 = inst(800), inst(500)

def glyph(font, ch):
    gs = font.getGlyphSet(); name = font.getBestCmap()[ord(ch)]
    pen = SVGPathPen(gs); gs[name].draw(pen)
    return pen.getCommands(), font['hmtx'][name][0]

def run(font, text, track=0):
    """Lista de (path, x) em unidades da fonte, e largura total."""
    out, x = [], 0
    for ch in text:
        d, adv = glyph(font, ch); out.append((d, x)); x += adv + track
    return out, x - track

# ---- wordmark: "dig" "." "D" (800) + "vídeo" (500)
def wordmark(cor_digd, cor_video, size, x0, base):
    s = size / 1000
    parts = []
    a, wa = run(F800, 'dig', -12)
    dot, wdot = run(F800, '.')
    D, wD = run(F800, 'D')
    v, wv = run(F500, 'vídeo', -6)
    x = 0
    segs = []
    for grupo, larg, cor, gap in ((a, wa, cor_digd, 10), (dot, wdot, ROSA, 6), (D, wD, cor_digd, 250), (v, wv, cor_video, 0)):
        for d, gx in grupo:
            segs.append((d, x + gx, cor))
        x += larg + gap
    for d, gx, cor in segs:
        parts.append(f'<path fill="{cor}" transform="translate({x0 + gx*s:.2f} {base:.2f}) scale({s:.5f} {-s:.5f})" d="{d}"/>')
    return '\n  '.join(parts), x * s

# ---- ícone 64x64: campo azul, D branco com o play vazado, ponto rosa (o ".D" da casa)
def icone(x=0, y=0, k=1.0, campo=True):
    g = []
    if campo:
        g.append(f'<rect width="64" height="64" rx="14" fill="{AZUL}"/>')
    g.append('<path fill="#FFFFFF" fill-rule="evenodd" d="M25 14H35A18 18 0 0 1 35 50H25Z M32.5 22.6Q31 21.8 31 23.4V40.6Q31 42.2 32.5 41.4L46 33.3Q47.4 32 46 30.7Z"/>')
    g.append(f'<circle cx="16" cy="45.5" r="4.5" fill="{ROSA}"/>')
    return f'<g transform="translate({x} {y}) scale({k})">' + ''.join(g) + '</g>'

def svg(w, h, body, titulo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{titulo}">\n'
            f'  <title>{titulo}</title>\n  {body}\n</svg>\n')

def salvar(nome, conteudo):
    open(f'{OUT}/{nome}', 'w').write(conteudo)

salvar('icone.svg', svg(64, 64, icone(), 'dig.D Vídeo'))
# favicon: em 16px o ponto rosa vira borrão de 2px. Sai o ponto, o D cresce e centraliza.
FAV = (f'<rect width="64" height="64" rx="13" fill="{AZUL}"/>'
       '<path fill="#FFFFFF" fill-rule="evenodd" d="M14 11H29A21 21 0 0 1 29 53H14Z M23.5 21.4Q22 20.6 22 22.4V41.6Q22 43.4 23.5 42.6L39 33.4Q40.6 32 39 30.6Z"/>')
salvar('favicon.svg', svg(64, 64, FAV, 'dig.D Vídeo'))

# horizontal: ícone 64 + wordmark, cap height ~ metade do ícone
for nome, cd, cv in (('logo-horizontal.svg', TINTA, AZUL), ('logo-horizontal-negativo.svg', CREME, CREME)):
    size = 46; cap = 0.7 * size
    wm, lw = wordmark(cd, cv, size, 82, 32 + cap/2)
    salvar(nome, svg(82 + lw + 2, 64, icone() + '\n  ' + wm, 'dig.D Vídeo'))

# principal (empilhado): ícone 112 centralizado sobre o wordmark
for nome, cd, cv in (('logo.svg', TINTA, AZUL), ('logo-negativo.svg', CREME, CREME)):
    size = 48
    _, lw = wordmark(cd, cv, size, 0, 0)
    W = max(lw, 112) + 8
    wm, _ = wordmark(cd, cv, size, (W - lw)/2, 112 + 22 + 0.7*size)
    salvar(nome, svg(W, 112 + 22 + 0.7*size + 0.24*size, icone((W-112)/2, 0, 112/64) + '\n  ' + wm, 'dig.D Vídeo'))
print('ok')
