#!/usr/bin/env python3
"""Folha de amostras: a mesma planta com todos os ambientes pintados em cada
paleta, lado a lado, pra escolher antes de montar a pagina.

uso: python ferramentas/amostras.py planta/X.comodos.ajustado.json [--modo setor]
     ->  planta/X.amostras.png
"""
import argparse, json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("comodos"); ap.add_argument("--modo", default="ambiente")
a = ap.parse_args()
PAL = json.load(open(os.path.join(AQUI, "paletas.json")))
ordem = [k for k in PAL if not k.startswith("_")]

try:
    fonte = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except OSError:
    fonte = ImageFont.load_default()

def pintar(pasta):
    """Recompoe a pagina com todos os ambientes acesos: planta, cor, linhas."""
    html = open(os.path.join(pasta, "index.html")).read()
    P = json.loads(re.search(r"var P = (.*?);\n", html).group(1))
    base = Image.open(os.path.join(pasta, "planta.jpg")).convert("RGBA")
    cam = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for c in P["comodos"]:
        for parte in re.findall(r"M([^Z]+)Z", c["d"]):
            pts = [tuple(map(float, q.split(","))) for q in parte.split()]
            d.polygon(pts, fill=c["cor"])
    linhas = Image.open(os.path.join(pasta, "linhas.png")).convert("RGBA")
    return Image.alpha_composite(Image.alpha_composite(base, cam), linhas)

quadros = []
with tempfile.TemporaryDirectory() as tmp:
    for k in ordem:
        pasta = os.path.join(tmp, k)
        r = subprocess.run([sys.executable, os.path.join(AQUI, "montar.py"), a.comodos, pasta,
                            "--paleta", k, "--modo", a.modo], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr)
        nome = PAL[k]["nome"]
        quadros.append((nome, pintar(pasta)))

L = 900
quadros = [(n, im.resize((L, round(im.height * L / im.width)), Image.LANCZOS)) for n, im in quadros]
h = quadros[0][1].height
M, T = 40, 56
linhas_ = (len(quadros) + 2) // 3
folha = Image.new("RGB", (M + 3 * (L + M), M + linhas_ * (h + T + M)), "#f5f3ef")
dd = ImageDraw.Draw(folha)
for i, (n, im) in enumerate(quadros):
    x, y = M + (i % 3) * (L + M), M + (i // 3) * (h + T + M)
    folha.paste(im.convert("RGB"), (x, y))
    dd.text((x, y + h + 14), n, fill="#1e1e1e", font=fonte)
saida = a.comodos.replace(".comodos.ajustado.json", "") + (".amostras-setor.png" if a.modo == "setor" else ".amostras.png")
folha.save(saida)
print(saida)
