#!/usr/bin/env python3
"""Prepara a planta pra leitura: PDF vira imagem (uma por pagina), o texto do
PDF sai com a posicao de cada palavra, e a imagem ganha a grade com
coordenadas que o Claude usa pra marcar os comodos.

uso: python ferramentas/preparar.py planta/arquivo.pdf [pagina]
     python ferramentas/preparar.py planta/arquivo.png
"""
import json, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
LARG = 2600                     # largura da imagem gerada a partir do PDF

src = sys.argv[1]
base, ext = os.path.splitext(src)
saidas = []

if ext.lower() == ".pdf":
    import fitz
    doc = fitz.open(src)
    paginas = [int(sys.argv[2])] if len(sys.argv) > 2 else range(1, len(doc) + 1)
    for n in paginas:
        pg = doc[n - 1]
        k = LARG / pg.rect.width
        png = f"{base}-p{n}.png" if len(doc) > 1 else f"{base}.png"
        pg.get_pixmap(matrix=fitz.Matrix(k, k), alpha=False).save(png)
        # PDF exportado do CAD traz o texto de verdade: nome e m2 de cada
        # comodo com a posicao exata, em pixels da imagem gerada
        textos = [[round(b[0] * k), round(b[1] * k), round(b[2] * k), round(b[3] * k), b[4]]
                  for b in pg.get_text("words") if b[4].strip()]
        if textos:
            json.dump(textos, open(png[:-4] + ".textos.json", "w"), ensure_ascii=False)
        saidas.append((png, len(textos)))
else:
    saidas.append((src, 0))

for png, n in saidas:
    r = subprocess.run([sys.executable, os.path.join(AQUI, "grade.py"), png], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip(), f"| textos no PDF: {n}" if n else "| sem texto (ler pela imagem)")
