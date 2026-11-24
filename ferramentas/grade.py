#!/usr/bin/env python3
"""Desenha uma grade com coordenadas por cima da planta, pro Claude ler a
posicao de cada comodo em pixels da imagem original.

uso: python ferramentas/grade.py planta/X.png [passo]  ->  planta/X.grade.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

src = sys.argv[1]
im = Image.open(src).convert("RGB")
W, H = im.size
passo = int(sys.argv[2]) if len(sys.argv) > 2 else (50 if W < 1800 else 100)
d = ImageDraw.Draw(im, "RGBA")
try:
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", max(11, W // 110))
except OSError:
    f = ImageFont.load_default()
for x in range(0, W, passo):
    forte = x % (passo * 2) == 0
    d.line([(x, 0), (x, H)], fill=(255, 0, 80, 120 if forte else 50), width=1)
    if forte:
        for y in range(0, H, passo * 4):
            d.text((x + 2, y + 2), str(x), fill=(255, 0, 80, 255), font=f)
for y in range(0, H, passo):
    forte = y % (passo * 2) == 0
    d.line([(0, y), (W, y)], fill=(0, 90, 255, 120 if forte else 50), width=1)
    if forte:
        for x in range(0, W, passo * 4):
            d.text((x + 2, y + 2), str(y), fill=(0, 90, 255, 255), font=f)
out = src.rsplit(".", 1)[0] + ".grade.png"
im.save(out)
print(out, W, H)
