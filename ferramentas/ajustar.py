#!/usr/bin/env python3
"""Encosta o recorte de cada comodo nas paredes.

O Claude le a planta e escreve comodos.json com o nome e um retangulo
aproximado por comodo (ou mais de um, se o comodo for em L). Aqui cada lado
desse retangulo procura, a ate FOLGA px, a linha em que a parede corre junto
dele, e para na face de dentro. Lado sem parede perto (espaco integrado,
passagem) fica onde o Claude marcou: so linha reta.

uso: python ferramentas/ajustar.py planta/X.png planta/X.comodos.json  ->  X.comodos.ajustado.json + X.comodos.conferir.png
"""
import json, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

FOLGA = 30          # quanto o lado pode andar procurando a parede (cresce com a imagem)
COBRE = 0.30        # fracao do lado que precisa estar encostada em parede
PERTO = 0.15        # perto da marcacao basta menos: parede com porta cobre pouco do lado

planta, arq = sys.argv[1], sys.argv[2]
cor = np.array(Image.open(planta).convert("RGB"))
cinza = cv2.cvtColor(cor, cv2.COLOR_RGB2GRAY)
H, W = cinza.shape
FOLGA = max(FOLGA, W // 60)
ALCANCE = W // 25       # ate onde procura a parede atras da marcenaria (mais longe que isso
                        # ja e outro espaco: fachada de vidro com jardim e muro depois)

def mascara_parede():
    """Parede = o que e escuro, neutro E grosso. Neutro porque marcenaria,
    sofa e piso de madeira escuros tem cor (saturacao acima de 12), e a parede
    e cinza ou preta. Planta de traco (CAD) nao tem parede grossa: ai a parede
    e a propria linha escura."""
    sat = cor.max(axis=2).astype(int) - cor.min(axis=2)
    escuro = ((cinza < 125) & (sat < 12)).astype(np.uint8)
    for k in (7, 5):
        grossa = cv2.morphologyEx(escuro, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        if grossa.sum() > 0.01 * W * H:
            return grossa, f"parede grossa ({k}px)"
    return ((cinza < 150) & (sat < 30)).astype(np.uint8), "traco"

P, estilo = mascara_parede()
# so na planta humanizada a marcenaria e desenho cheio que o Claude confunde
# com fora do comodo; na de traco a parede longe e quase sempre de outro espaco
_sat = cor.max(axis=2).astype(int) - cor.min(axis=2)
COLORIDA = bool(np.median(_sat[cinza < 240]) > 10)

def cobertura(eixo, pos, a, b):
    a, b = max(0, a), min(W if eixo == "y" else H, b)
    if eixo == "x":          # coluna x=pos, de y=a a b
        if not 0 <= pos < W: return 0
        return P[a:b, pos].mean() if b > a else 0
    if not 0 <= pos < H: return 0
    return P[pos, a:b].mean() if b > a else 0

def encostar(eixo, pos, a, b, dentro, limite=None):
    """Acha a parede perto de pos e devolve a face do lado de dentro.
    dentro = +1 se o comodo fica para o lado crescente, -1 se decrescente.
    Sem parede perto, procura mais longe para fora: armario embutido e
    marcenaria fazem parte do comodo, a borda vai ate a parede atras deles.
    `limite` e onde comeca o comodo vizinho: dali nao passa."""
    m = (b - a) // 8               # ignora as pontas (canto, porta)
    a2, b2 = a + m, b - m
    # a parede mais perto da marcacao, nao a mais forte: o Claude marcou
    # perto da face certa, e a linha de fora da parede tambem e escura
    melhor, nota = None, 0
    for d in range(0, FOLGA + 1):
        for p in ((pos - d, pos + d) if d else (pos,)):
            c = cobertura(eixo, p, a2, b2)
            if c >= PERTO and c > nota:
                melhor, nota = p, c
        if melhor is not None:
            break
    if melhor is None and COLORIDA:
        fim = pos - dentro * ALCANCE
        if limite is not None:
            fim = max(fim, limite) if dentro > 0 else min(fim, limite)
        for p in range(pos - dentro * FOLGA, fim - dentro, -dentro):
            c = cobertura(eixo, p, a2, b2)
            if c >= COBRE:
                melhor, nota = p, c
                break
    if melhor is None:
        return pos, False
    p = melhor                      # anda ate sair da parede, para dentro
    while cobertura(eixo, p + dentro, a2, b2) >= nota * 0.5 and abs(p - melhor) < 40:
        p += dentro
    p += dentro
    # nunca entra no comodo vizinho
    if limite is not None:
        p = max(p, limite) if dentro > 0 else min(p, limite)
    return p, True

D = json.load(open(arq))

def vizinho(c, r, lado):
    """Onde comeca o comodo vizinho daquele lado (entre os outros comodos que
    dividem boa parte do lado com este retangulo)."""
    x0, y0, x1, y1 = r
    lim = None
    for o in D["comodos"]:
        if o is c:
            continue
        for q in o["retangulos"]:
            if lado in "es":     # esquerda/direita: precisa dividir faixa em y
                junto = min(y1, q[3]) - max(y0, q[1]) > 0.2 * min(y1 - y0, q[3] - q[1])
                if lado == "e" and junto and q[2] <= x0 + 2: lim = q[2] if lim is None else max(lim, q[2])
                if lado == "s" and junto and q[0] >= x1 - 2: lim = q[0] if lim is None else min(lim, q[0])
            else:                # cima/baixo: precisa dividir faixa em x
                junto = min(x1, q[2]) - max(x0, q[0]) > 0.2 * min(x1 - x0, q[2] - q[0])
                if lado == "c" and junto and q[3] <= y0 + 2: lim = q[3] if lim is None else max(lim, q[3])
                if lado == "b" and junto and q[1] >= y1 - 2: lim = q[1] if lim is None else min(lim, q[1])
    return lim

def costura(c, r, lado):
    """O lado encosta em outro retangulo do mesmo comodo (comodo em L): e
    costura interna, fica onde o Claude marcou, senao o comodo parte ao meio."""
    x0, y0, x1, y1 = r
    for q in c["retangulos"]:
        if q is r:
            continue
        if lado in "es" and min(y1, q[3]) - max(y0, q[1]) > 0:
            if lado == "e" and abs(q[2] - x0) <= 3: return True
            if lado == "s" and abs(q[0] - x1) <= 3: return True
        if lado in "cb" and min(x1, q[2]) - max(x0, q[0]) > 0:
            if lado == "c" and abs(q[3] - y0) <= 3: return True
            if lado == "b" and abs(q[1] - y1) <= 3: return True
    return False

def lado(c, r, qual, eixo, pos, a, b, dentro):
    if costura(c, r, qual):
        return pos
    return encostar(eixo, pos, a, b, dentro, vizinho(c, r, qual))[0]

for c in D["comodos"]:
    novos = []
    for r in c["retangulos"]:
        x0, y0, x1, y1 = r
        novos.append([lado(c, r, "e", "x", x0, y0, y1, +1), lado(c, r, "c", "y", y0, x0, x1, +1),
                      lado(c, r, "s", "x", x1, y0, y1, -1), lado(c, r, "b", "y", y1, x0, x1, -1)])
    c["recorte"] = novos

def alinhar(ix):
    """Coordenadas quase iguais viram uma so (ideia tirada do Inverse
    Algorithmic Design, que agrupa os x e os y dos pontos): dois ambientes
    integrados dividem a mesma linha, sem fresta nem sobreposicao, e as bordas
    alinhadas na planta saem alinhadas na pagina."""
    tol = max(4, W // 300)
    vals = sorted({r[i] for c in D["comodos"] for r in c["recorte"] for i in ix})
    grupos, atual = [], [vals[0]] if vals else []
    for v in vals[1:]:
        if v - atual[-1] <= tol: atual.append(v)
        else: grupos.append(atual); atual = [v]
    if atual: grupos.append(atual)
    troca = {v: round(sum(g) / len(g)) for g in grupos for v in g}
    for c in D["comodos"]:
        for r in c["recorte"]:
            for i in ix: r[i] = troca[r[i]]

alinhar((0, 2))
alinhar((1, 3))
def mascara(c):
    """Area do comodo: os retangulos mais os bolsoes que completam ate a parede."""
    mk = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in c["recorte"]:
        mk[y0:y1, x0:x1] = 1
    for bo in c.get("bolsoes", []):
        cv2.fillPoly(mk, [np.array(bo, np.int32)], 1)
    for co in c.get("cortes", []):
        cv2.fillPoly(mk, [np.array(co, np.int32)], 0)
    return mk

# dentro da casa = o maior contorno fechado do desenho (parede externa), com as
# frestas de porta e janela costuradas. Livre = piso: sem traco, parede nem
# parede pintada de cinza (poche do desenho de CAD)
_tinta = (cinza < 160).astype(np.uint8)
_cs, _ = cv2.findContours(cv2.morphologyEx(_tinta, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)),
                          cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
CASA = np.zeros((H, W), np.uint8)
if _cs:
    cv2.drawContours(CASA, [max(_cs, key=cv2.contourArea)], -1, 1, -1)
TINTA = cv2.dilate(_tinta, np.ones((5, 5), np.uint8))
POCHE = (_sat < 12) & (cinza < 225)
LIVRE = (CASA > 0) & (TINTA == 0) & (P == 0) & ~POCHE
# o mesmo sem engrossar o traco: linha tracejada (arco de porta) deixa passar,
# linha continua (parede curva, bancada) separa
LIVRE_FINO = (CASA > 0) & (_tinta == 0) & (P == 0) & ~POCHE


def completar():
    """Parede curva, canto chanfrado, sobra entre o retangulo e a parede: o
    piso que ficou fora dos retangulos, cercado de parede e encostado em UM
    ambiente so, vira parte dele (bolsao). Onde a parede e reta a borda segue
    reta; onde e curva, acompanha a curva. Encostado em dois ambientes (porta,
    passagem) nao e de ninguem: fica pro aviso de area sem dono."""
    mks = [mascara(c) for c in D["comodos"]]
    uniao = np.zeros((H, W), np.uint8)
    for mk in mks: uniao |= mk
    livre = (LIVRE & (uniao == 0)).astype(np.uint8)
    n, rot, st, _ = cv2.connectedComponentsWithStats(livre, connectivity=4)
    G = 2              # encosta direto, piso com piso: atras de parede ou de traco nao conta (jardim)
    for k in range(1, n):
        x, y, w, h, a_ = st[k]
        # miolo de parede hachurada e lasca junto da parede nao contam
        if a_ < max(200, 0.00012 * W * H) or x == 0 or y == 0 or x + w >= W or y + h >= H:
            continue
        x0, y0, x1, y1 = max(0, x - G - 2), max(0, y - G - 2), min(W, x + w + G + 2), min(H, y + h + G + 2)
        comp = (rot[y0:y1, x0:x1] == k).astype(np.uint8)
        perto = cv2.dilate(comp, np.ones((2 * G + 1, 2 * G + 1), np.uint8))
        # de quem e: do ambiente que encosta em pelo menos 80% da borda do
        # bolsao (o resto e o vizinho do outro lado de uma parede fina)
        # so conta encostar em piso do comodo (o traco da parede curva nao vale)
        piso = LIVRE[y0:y1, x0:x1]
        toque = [(int((perto & mk[y0:y1, x0:x1] & piso).sum()), i) for i, mk in enumerate(mks)]
        total = sum(t for t, _ in toque)
        t, i = max(toque)
        if t < 20 or t < 0.8 * total or a_ > 0.3 * mks[i].sum():
            continue
        # e o mesmo piso? jardim, piscina e calcada tem outra cor e ficam fora
        piso_comodo = cor[(mks[i] > 0) & LIVRE]
        piso_bolsao = cor[y0:y1, x0:x1][comp > 0]
        if len(piso_comodo) and np.linalg.norm(np.median(piso_comodo, 0) - np.median(piso_bolsao, 0)) > 40:
            continue
        # cobre o traco ate o retangulo, sem entrar em parede nem em outro comodo
        outros = uniao[y0:y1, x0:x1] & (1 - mks[i][y0:y1, x0:x1])
        bo = perto & (P[y0:y1, x0:x1] == 0) & (outros == 0)
        cs, _ = cv2.findContours(bo, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cs:
            if cv2.contourArea(cnt) < 30:
                continue
            ap = cv2.approxPolyDP(cnt, 1.5, True).reshape(-1, 2) + [x0, y0]
            D["comodos"][i].setdefault("bolsoes", []).append(ap.tolist())


def aparar():
    """O contrario do bolsao: parede curva (ou canto chanfrado) que corta o
    retangulo por dentro. O pedaco de piso que a parede separa do resto do
    comodo e que continua do lado de fora (no vizinho) sai do comodo (corte)."""
    for c in D["comodos"]:
        mk = mascara(c)
        dentro = (mk & LIVRE_FINO).astype(np.uint8)
        n, rot, st, _ = cv2.connectedComponentsWithStats(dentro, connectivity=4)
        if n <= 2:
            continue
        principal = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        for k in range(1, n):
            x, y, w, h, a_ = st[k]
            if k == principal or a_ < max(150, 0.00005 * W * H) or a_ > 0.08 * mk.sum():
                continue
            # so canto: o pedaco encosta em dois lados que se cruzam de um mesmo
            # retangulo (canto arredondado). Pedaco cercado por movel encosta em
            # um lado so e e do comodo
            canto = False
            for rx0, ry0, rx1, ry1 in c["recorte"]:
                if x < rx0 - 3 or y < ry0 - 3 or x + w > rx1 + 3 or y + h > ry1 + 3:
                    continue
                esq, dir_ = abs(x - rx0) <= 3, abs(x + w - rx1) <= 3
                cima, baixo = abs(y - ry0) <= 3, abs(y + h - ry1) <= 3
                if (esq or dir_) and (cima or baixo):
                    canto = True
            if not canto:
                continue
            x0, y0, x1, y1 = max(0, x - 4), max(0, y - 4), min(W, x + w + 4), min(H, y + h + 4)
            comp = (rot[y0:y1, x0:x1] == k).astype(np.uint8)
            borda = cv2.dilate(comp, np.ones((5, 5), np.uint8)) & (1 - mk[y0:y1, x0:x1])
            if int((borda & LIVRE_FINO[y0:y1, x0:x1]).sum()) < 15:
                continue                       # fechado por traco dentro do comodo: e dele
            corte = cv2.dilate(comp, np.ones((5, 5), np.uint8)) & mk[y0:y1, x0:x1] & (TINTA[y0:y1, x0:x1] == 0)
            cs, _ = cv2.findContours(corte, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in cs:
                if cv2.contourArea(cnt) >= 30:
                    ap = cv2.approxPolyDP(cnt, 1.5, True).reshape(-1, 2) + [x0, y0]
                    c.setdefault("cortes", []).append(ap.tolist())


aparar()
completar()


def conferir():
    """Avisos pro Claude corrigir antes de mostrar: recorte que atravessa
    parede (corredor fatiado, vazamento), comodos sobrepostos, numero do
    ambiente fora do lugar (PDF com numeros) e area fora do m2 da planta."""
    av = []
    for c in D["comodos"]:
        if "escada" in c["nome"].lower():
            av.append(f'{c["nome"]}: escada nao e ambiente. Junte ao ambiente em que ela esta inserida.')
    for c in D["comodos"]:
        for x0, y0, x1, y1 in c["recorte"]:
            m = max(12, W // 160)       # parede encostada na borda nao conta
            for y in range(y0 + m, y1 - m):
                if (x1 - x0) > 40 and P[y, x0:x1].mean() >= 0.5:
                    av.append(f'{c["nome"]}: uma parede atravessa o recorte na altura y={y}. Corredor ou outro espaco entrou junto?'); break
            for x in range(x0 + m, x1 - m):
                if (y1 - y0) > 40 and P[y0:y1, x].mean() >= 0.5:
                    av.append(f'{c["nome"]}: uma parede atravessa o recorte na coluna x={x}. Corredor ou outro espaco entrou junto?'); break
    mks = [mascara(c) for c in D["comodos"]]
    for i in range(len(mks)):
        for j in range(i + 1, len(mks)):
            inter = int((mks[i] & mks[j]).sum())
            if inter > 0.02 * min(mks[i].sum(), mks[j].sum()):
                av.append(f'{D["comodos"][i]["nome"]} e {D["comodos"][j]["nome"]} se sobrepoem.')
    txt = planta.rsplit(".", 1)[0] + ".textos.json"
    if os.path.exists(txt) and any("numero" in c for c in D["comodos"]):
        selos = [t for t in json.load(open(txt)) if t[4].strip().isdigit()]
        for i, c in enumerate(D["comodos"]):
            if "numero" not in c: continue
            meus = [t for t in selos if int(t[4]) == int(c["numero"])]
            dentro = lambda t, mk: mk[min(H - 1, (t[1] + t[3]) // 2), min(W - 1, (t[0] + t[2]) // 2)] > 0
            if meus and not any(dentro(t, mks[i]) for t in meus):
                av.append(f'{c["nome"]}: o numero {c["numero"]} ficou fora do recorte.')
            for t in selos:
                n = int(t[4])
                if n != int(c["numero"]) and dentro(t, mks[i]) and any(int(o.get("numero", -1)) == n for o in D["comodos"]):
                    av.append(f'{c["nome"]}: o recorte pegou o numero {n}, de outro ambiente.')
    # area sem dono: piso que ficou fora de todos os recortes mas esta cercado
    # por eles (o fechamento da uniao com um raio grande acha os buracos e
    # reentrancias entre ambientes; fora da casa fica de fora)
    uniao = np.zeros((H, W), np.uint8)
    for mk in mks: uniao |= mk
    sobra = LIVRE & (uniao == 0)
    # faixa fina (miolo de parede dupla, fresta entre recortes) nao conta
    k = max(9, int(0.02 * max(W, H)))
    sobra = cv2.morphologyEx(sobra.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    n, rot, st, _ = cv2.connectedComponentsWithStats(sobra)
    for k in range(1, n):
        x, y, w, h, a_ = st[k]
        if a_ > 0.006 * uniao.sum():
            av.append(f'Area sem dono entre x={x}-{x + w} e y={y}-{y + h}. Se e piso da casa, junte ao ambiente dela (escada e passagem inclusive); se e area externa ou jardim, ignore.')
    com_m2 = [(c, mks[i].sum()) for i, c in enumerate(D["comodos"]) if c.get("m2")]
    if len(com_m2) >= 3:
        esc = float(np.median([a / c["m2"] for c, a in com_m2]))
        for c, a in com_m2:
            r = a / esc / c["m2"]
            if abs(r - 1) > 0.25:
                av.append(f'{c["nome"]}: recorte com {a / esc:.1f} m2, a planta diz {c["m2"]} m2.')
    return av

D["avisos"] = conferir()
D["estilo"] = estilo
D["planta"] = {"arquivo": planta, "w": W, "h": H}
saida = arq.rsplit(".", 1)[0] + ".ajustado.json"
json.dump(D, open(saida, "w"), ensure_ascii=False, indent=1)

# conferencia: cada comodo numa cor, com o nome
PAL = [(196, 140, 92), (120, 150, 120), (110, 135, 170), (190, 120, 120), (170, 150, 100),
       (140, 120, 170), (100, 160, 160), (200, 170, 120), (150, 110, 90)]
im = Image.fromarray(cor).convert("RGBA")
cam = Image.new("RGBA", im.size, (0, 0, 0, 0))
d = ImageDraw.Draw(cam)
try:
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", max(14, W // 70))
except OSError:
    f = ImageFont.load_default()
for i, c in enumerate(D["comodos"]):
    r, g, b = PAL[i % len(PAL)]
    for (x0, y0, x1, y1) in c["recorte"]:
        d.rectangle([x0, y0, x1, y1], fill=(r, g, b, 150), outline=(r, g, b, 255), width=2)
    for bo in c.get("bolsoes", []):
        d.polygon([tuple(p) for p in bo], fill=(r, g, b, 150))
for c in D["comodos"]:
    for co in c.get("cortes", []):
        d.polygon([tuple(p) for p in co], fill=(255, 255, 255, 170))
for c in D["comodos"]:
    x0, y0, x1, y1 = max(c["recorte"], key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), c["nome"], fill=(20, 20, 20, 255), font=f, anchor="mm")
Image.alpha_composite(im, cam).convert("RGB").save(arq.rsplit(".", 1)[0] + ".conferir.png")
print(saida, estilo, len(D["comodos"]), "comodos")
if D["avisos"]:
    print(f'{len(D["avisos"])} avisos para conferir:')
    for a_ in D["avisos"]:
        print(" -", a_)
else:
    print("conferencia automatica: nenhum aviso")
