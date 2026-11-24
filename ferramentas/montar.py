#!/usr/bin/env python3
"""Monta a planta animada a partir da planta e do comodos.ajustado.json.

Sai uma pasta com index.html, planta.jpg e linhas.png, que abre direto no
navegador e sobe em qualquer hospedagem de site estatico.

A cor de cada comodo e a que predomina no piso dele na propria planta
(planta humanizada). Planta de traco, sem cor, usa a paleta neutra.

Paleta: --paleta paleta1 (padrao) a paleta5, ou --cores com as cores do
escritorio. --modo setor pinta pelo setor do comodo (social, intimo,
servico, molhado, circulacao, externo) em vez de uma cor por ambiente.

uso: python ferramentas/montar.py planta/X.comodos.ajustado.json saida/X --titulo "Casa X" [--paleta terra] [--modo setor] [--cores "#hex,#hex"]
"""
import argparse, json, os
import numpy as np, cv2
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
NEUTRA = ["#C9BFB1", "#B8AE9F", "#D6CCBE", "#A9A196", "#CFC4B4", "#BDB3A6", "#C2B8A8", "#ADA597"]
LARG = 2400                       # a planta sai no maximo com esta largura

ap = argparse.ArgumentParser()
ap.add_argument("comodos"); ap.add_argument("saida")
ap.add_argument("--titulo", default="")
ap.add_argument("--cores", default="", help="cores da identidade do escritorio, separadas por virgula")
ap.add_argument("--paleta", default="", help="paleta1 a paleta5 (paletas.json)")
ap.add_argument("--modo", default="ambiente", choices=["ambiente", "setor"])
a = ap.parse_args()
arq, saida, titulo = a.comodos, a.saida, a.titulo
PALETAS = json.load(open(os.path.join(AQUI, "paletas.json")))
SETORES = ["social", "intimo", "servico", "molhado", "circulacao", "externo"]
NEUTRA = PALETAS["paleta1"]["cores"]   # padrao: so paletas coloridas
PROPRIAS = [c.strip() for c in a.cores.split(",") if c.strip()]
if not PROPRIAS and not a.paleta:
    a.paleta = "paleta1"
if not PROPRIAS and a.paleta and a.paleta != "piso":
    PROPRIAS = PALETAS[a.paleta]["cores"]
D = json.load(open(arq))
src = D["planta"]["arquivo"]
if not os.path.exists(src):
    src = os.path.join(os.path.dirname(arq), os.path.basename(src))
im = Image.open(src).convert("RGB")
# recorta a imagem em volta dos comodos: moldura, carimbo e legenda da
# prancha ficam de fora
xs = [v for c in D["comodos"] for r in c["recorte"] for v in (r[0], r[2])]
ys = [v for c in D["comodos"] for r in c["recorte"] for v in (r[1], r[3])]
mg = round(0.015 * max(max(xs) - min(xs), max(ys) - min(ys)))   # margem curta: a legenda da prancha fica de fora
cx, cy = max(0, min(xs) - mg), max(0, min(ys) - mg)
im = im.crop((cx, cy, min(im.width, max(xs) + mg), min(im.height, max(ys) + mg)))
for c in D["comodos"]:
    c["recorte"] = [[r[0] - cx, r[1] - cy, r[2] - cx, r[3] - cy] for r in c["recorte"]]
    c["bolsoes"] = [[[p[0] - cx, p[1] - cy] for p in bo] for bo in c.get("bolsoes", [])]
    c["cortes"] = [[[p[0] - cx, p[1] - cy] for p in co] for co in c.get("cortes", [])]
k = min(1.0, LARG / im.width)
if k < 1:
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
W, H = im.size
cor = np.array(im)
cinza = cv2.cvtColor(cor, cv2.COLOR_RGB2GRAY)
sat = cor.max(axis=2).astype(int) - cor.min(axis=2)
os.makedirs(saida, exist_ok=True)
im.save(os.path.join(saida, "planta.jpg"), quality=88)

# linhas: vai por cima da cor (a cor nunca cobre a parede).
# Planta de traco: todo o traco escuro. Planta humanizada (colorida): so a
# parede, escura, neutra e grossa; marcenaria e sombra de movel ficam embaixo
colorida = np.median(sat[cinza < 240]) > 10
if colorida:
    p = ((cinza < 125) & (sat < 12)).astype(np.uint8)
    p = cv2.morphologyEx(p, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    tinta = cv2.dilate(p, np.ones((3, 3), np.uint8)) * 255
else:
    tinta = ((cinza < 140) & (sat < 30)).astype(np.uint8) * 255
la = np.zeros((H, W, 4), np.uint8)
la[..., :3] = cor
la[..., 3] = cv2.GaussianBlur(tinta, (3, 3), 0)
Image.fromarray(la).save(os.path.join(saida, "linhas.png"), optimize=True)

def contorno(rets, bolsoes=(), cortes=()):
    """Uniao dos retangulos e dos bolsoes (o que completa ate a parede curva)
    como um caminho so: reto onde a parede e reta, curvo onde ela e curva."""
    m = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in rets:
        cv2.rectangle(m, (round(x0 * k), round(y0 * k)), (round(x1 * k), round(y1 * k)), 255, -1)
    for bo in bolsoes:
        cv2.fillPoly(m, [np.array([[round(x * k), round(y * k)] for x, y in bo], np.int32)], 255)
    for co in cortes:
        cv2.fillPoly(m, [np.array([[round(x * k), round(y * k)] for x, y in co], np.int32)], 0)
    if bolsoes or cortes:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return " ".join("M" + " ".join(f"{p[0][0]},{p[0][1]}" for p in c) + "Z" for c in cs), m

def predominante(m):
    """Cor do piso: k-means nos pixels claros e coloridos do comodo, fica o
    grupo maior. Sem cor (planta de traco) devolve None."""
    px = cor[(m > 0) & (cinza > 110) & (cinza < 245)]
    if len(px) < 200 or np.median(sat[(m > 0) & (cinza > 110)]) < 14:
        return None
    px = px[:: max(1, len(px) // 20000)].astype(np.float32)
    _, rot, cen = cv2.kmeans(px, 3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1), 3, cv2.KMEANS_PP_CENTERS)
    c = cen[np.bincount(rot.ravel()).argmax()]
    return "#%02X%02X%02X" % tuple(int(v) for v in c)

def cor_do(c, i, m):
    pal = PROPRIAS or NEUTRA
    if a.modo == "setor":
        k = SETORES.index(c["setor"]) if c.get("setor") in SETORES else len(SETORES) - 2
        return pal[k % len(pal)]
    if PROPRIAS:
        return pal[i % len(pal)]
    return predominante(m) or NEUTRA[i % len(NEUTRA)]

comodos = []
for i, c in enumerate(D["comodos"]):
    d, m = contorno(c["recorte"], c.get("bolsoes", []), c.get("cortes", []))
    ys, xs = np.nonzero(m)
    comodos.append({
        "nome": c["nome"], "m2": c.get("m2"), "texto": c.get("texto", ""),
        "d": d, "caixa": [int(xs.min()), int(ys.min()), int(xs.max() - xs.min()), int(ys.max() - ys.min())],
        "cor": cor_do(c, i, m), "setor": c.get("setor"), "piso": predominante(m),
    })

dados = {"titulo": titulo, "w": W, "h": H, "comodos": comodos,
         "paleta": a.paleta or ("piso" if not PROPRIAS else "propria"), "modo": a.modo}
html = open(os.path.join(AQUI, "molde.html")).read()
def tema():
    """Cores da pagina quando a paleta traz as suas (papel, tinta, borda). O
    cinza do texto secundario sai da mistura de tinta e papel, escuro o
    bastante para ler (contraste acima de 4,5)."""
    pg = PALETAS.get(a.paleta, {}).get("pagina") if a.paleta else None
    if not pg:
        return ""
    hx = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    def lum(c):
        v = [x / 255 for x in c]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    t, p = hx(pg["tinta"]), hx(pg["papel"])
    for k in (0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9):
        c = [round(k * t[i] + (1 - k) * p[i]) for i in range(3)]
        l1, l2 = lum(c), lum(p)
        if (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05) >= 4.6:
            break
    cinza = "#%02X%02X%02X" % tuple(c)
    return (f":root {{ --papel: {pg['papel']}; --tinta: {pg['tinta']}; "
            f"--cinza: {cinza}; --bronze: {pg.get('borda', '#9a7b4f')}; }}")

html = html.replace("{{titulo}}", titulo or "Planta").replace("/*DADOS*/", json.dumps(dados, ensure_ascii=False))
# entre marcadores: o painel de cor (cores.py) reescreve so este trecho
html = html.replace("/*TEMA*/", "/*TEMA*/" + tema() + "/*FIM-TEMA*/")
open(os.path.join(saida, "index.html"), "w").write(html)
print(saida, W, H, len(comodos), "comodos")
