#!/usr/bin/env python3
"""Painel de cor: abre a pagina pronta no navegador com um painel do lado, pra
quem projetou escolher a paleta, o tom e a cor de cada ambiente vendo a planta.
Salvar grava direto no index.html da pasta. Concluir grava e encerra.

O painel so existe aqui: a pagina que vai pro cliente continua limpa.

uso: python ferramentas/cores.py saida/NOME      (rodar em segundo plano)
     --sem-abrir  nao abre o navegador sozinho
"""
import http.server, json, os, re, socket, sys, threading, webbrowser

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.abspath(sys.argv[1])
INDEX = os.path.join(PASTA, "index.html")
INJETAR = '<script src="/__painel.js"></script>\n</body>'


def porta_livre(p=3700):
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)):
                return p
        p += 1


def salvar(d):
    """Troca as cores no `var P = {...};` e o tema entre os marcadores."""
    html = open(INDEX, encoding="utf-8").read()
    m = re.search(r"var P = (.*?);\n", html)
    P = json.loads(m.group(1))
    for c, cor in zip(P["comodos"], d["cores"]):
        c["cor"] = cor
    P["paleta"], P["modo"] = d.get("paleta", P.get("paleta")), d.get("modo", P.get("modo"))
    html = html[:m.start(1)] + json.dumps(P, ensure_ascii=False) + html[m.end(1):]
    t = d["tema"]
    tema = (f":root {{ --papel: {t['papel']}; --tinta: {t['tinta']}; "
            f"--cinza: {t['cinza']}; --bronze: {t['borda']}; }}")
    html = re.sub(r"/\*TEMA\*/.*?/\*FIM-TEMA\*/", lambda _: "/*TEMA*/" + tema + "/*FIM-TEMA*/", html, flags=re.S)
    open(INDEX, "w", encoding="utf-8").write(html)


class Painel(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PASTA, **k)

    def log_message(self, *a):
        pass

    def responder(self, corpo, tipo):
        b = corpo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        rota = self.path.split("?")[0]
        if rota in ("/", "/index.html"):
            return self.responder(open(INDEX, encoding="utf-8").read().replace("</body>", INJETAR, 1),
                                  "text/html; charset=utf-8")
        if rota == "/__painel.js":
            return self.responder(open(os.path.join(AQUI, "painel.js"), encoding="utf-8").read(),
                                  "text/javascript; charset=utf-8")
        if rota == "/__paletas.json":
            return self.responder(open(os.path.join(AQUI, "paletas.json"), encoding="utf-8").read(),
                                  "application/json; charset=utf-8")
        return super().do_GET()

    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        salvar(d)
        self.responder('{"ok": true}', "application/json")
        print("salvo:", d.get("paleta"), d.get("modo"), flush=True)
        if self.path == "/concluir":
            threading.Thread(target=self.server.shutdown).start()


p = porta_livre()
srv = http.server.ThreadingHTTPServer(("127.0.0.1", p), Painel)
url = f"http://127.0.0.1:{p}/"
print("painel de cor em", url, "(Concluir no painel encerra)", flush=True)
if "--sem-abrir" not in sys.argv:
    webbrowser.open(url)
srv.serve_forever()
print("concluido: cores gravadas em", INDEX, flush=True)
