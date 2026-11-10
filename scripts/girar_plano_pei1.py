"""Gira 180° el plano (la mesa del profesor pasa arriba a la izquierda) dejando
el texto derecho y el título arriba. Uso: girar.py entrada.svg salida.svg"""
import re, sys
src = open(sys.argv[1]).read()
W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src).groups())
head, body = src.split('</defs>\n', 1)
body = body.rsplit('</svg>', 1)[0]
# Caja de cada glifo
caja = {}
for gid, d in re.findall(r'<g id="(glyph-[\d-]+)">\s*<path[^>]* d="([^"]*)"', head):
    n = list(map(float, re.findall(r'-?\d+(?:\.\d+)?', d)))
    xs, ys = n[0::2], n[1::2]
    caja[gid] = (min(xs), min(ys), max(xs), max(ys)) if n else (0, 0, 0, 0)
# Separar en trazos (paths) y grupos de texto
piezas = re.findall(r'(<path[^>]*/>|<g [^>]*>.*?</g>)', body, re.S)
rects = [p for p in piezas if p.startswith('<path') and 'evenodd' in p]
ytab = min(min(map(float, re.findall(r'-?\d+\.?\d*', re.search(r' d="([^"]*)"', p).group(1))[1::2])) for p in rects)
cy, cx = (ytab + H) / 2, W / 2
fijo, giro = [], []
for p in piezas:
    if not p.startswith('<g '):
        giro.append(p); continue
    attrs = re.match(r'<g ([^>]*)>', p).group(1)
    uses = [(g, float(x), float(y)) for g, x, y in re.findall(r'<use xlink:href="#([^"]+)" x="([^"]+)" y="([^"]+)"/>', p)]
    runs, run = [], []
    for u in uses:
        if run and (abs(u[2] - run[-1][2]) > 0.5 or u[1] - run[-1][1] > 20):
            runs.append(run); run = []
        run.append(u)
    if run: runs.append(run)
    for r in runs:
        v = [(x, y, caja[g]) for g, x, y in r if g in caja]   # los espacios no tienen trazo
        if not v: continue
        x0 = min(x + c[0] for x, y, c in v); x1 = max(x + c[2] for x, y, c in v)
        y0 = min(y + c[1] for x, y, c in v); y1 = max(y + c[3] for x, y, c in v)
        txt = ''.join(f'<use xlink:href="#{g}" x="{x}" y="{y}"/>' for g, x, y in r)
        if y1 < ytab:   # título: se queda arriba, sin girar
            fijo.append(f'<g {attrs}>{txt}</g>')
        else:           # contragiro sobre su centro: queda derecho en su sitio girado
            giro.append(f'<g {attrs} transform="rotate(180 {(x0+x1)/2:.3f} {(y0+y1)/2:.3f})">{txt}</g>')
out = (head + '</defs>\n' + '\n'.join(fijo) +
       f'\n<g transform="rotate(180 {cx:.3f} {cy:.3f})">\n' + '\n'.join(giro) + '\n</g>\n</svg>\n')
open(sys.argv[2], 'w').write(out)
print(sys.argv[2], 'fijos', len(fijo), 'girados', len(giro))
