/* Painel de cor do Leitor de Planta. So entra quando a pagina abre pelo
   ferramentas/cores.py; a pagina publicada nao carrega este arquivo. */
(function () {
  var L = window.LEITOR; if (!L) return;
  var P = L.P;
  var SETORES = ["social", "intimo", "servico", "molhado", "circulacao", "externo"];
  var NOME_SETOR = { social: "Social", intimo: "Íntimo", servico: "Serviço", molhado: "Molhado", circulacao: "Circulação", externo: "Externo" };
  var PADRAO = { papel: "#f5f3ef", tinta: "#1e1e1e", borda: "#9a7b4f" };

  /* ---------- cor ---------- */
  function rgb(h) { return [1, 3, 5].map(function (i) { return parseInt(h.slice(i, i + 2), 16); }); }
  function hex(c) { return "#" + c.map(function (v) { v = Math.max(0, Math.min(255, Math.round(v))); return (v < 16 ? "0" : "") + v.toString(16); }).join("").toUpperCase(); }
  function hsl(c) {
    var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, M = Math.max(r, g, b), m = Math.min(r, g, b), l = (M + m) / 2, h = 0, s = 0, d = M - m;
    if (d) { s = l > .5 ? d / (2 - M - m) : d / (M + m); h = M === r ? (g - b) / d + (g < b ? 6 : 0) : M === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6; }
    return [h, s, l];
  }
  function rgbDe(h, s, l) {
    function f(p, q, t) { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < .5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; }
    if (!s) return [l * 255, l * 255, l * 255];
    var q = l < .5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
    return [f(p, q, h + 1 / 3) * 255, f(p, q, h) * 255, f(p, q, h - 1 / 3) * 255];
  }
  /* tom: mistura com um quente (+) ou um frio (-), mantendo a claridade */
  function ajustar(h0, tom, inten, clar) {
    var c = rgb(h0), alvo = tom > 0 ? [232, 150, 90] : [90, 140, 200], k = Math.abs(tom) * .35;
    var l0 = hsl(c)[2];
    c = c.map(function (v, i) { return v + (alvo[i] - v) * k; });
    var x = hsl(c);
    return hex(rgbDe(x[0], Math.min(1, x[1] * inten), Math.max(.08, Math.min(.95, l0 + clar))));
  }
  function lum(h) { return rgb(h).map(function (v) { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }).reduce(function (a, v, i) { return a + v * [.2126, .7152, .0722][i]; }, 0); }
  function contraste(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); }
  function cinzaDe(tinta, papel) {
    var t = rgb(tinta), p = rgb(papel), c;
    for (var k = .55; k <= .95; k += .05) { c = hex(t.map(function (v, i) { return k * v + (1 - k) * p[i]; })); if (contraste(c, papel) >= 4.6) break; }
    return c;
  }

  /* ---------- estado ---------- */
  var PAL = {}, est = { paleta: P.paleta, modo: P.modo || "ambiente", tom: 0, inten: 1, clar: 0, fixas: {}, tema: {} };
  var temPiso = false;   // so paletas coloridas (31/10): a cor do piso saiu do painel

  function chave(i) { return est.modo === "setor" ? (P.comodos[i].setor || "circulacao") : String(i); }
  function base(i) {
    var nome = est.paleta, c = P.comodos[i];
    if (nome === "piso" && est.modo === "ambiente" && c.piso) return c.piso;
    var p = PAL[nome] || PAL.paleta1, n = p.cores.length;
    if (est.modo === "setor") { var k = SETORES.indexOf(c.setor); return p.cores[(k < 0 ? 4 : k) % n]; }
    return p.cores[i % n];
  }
  function final(i) { var k = chave(i); return est.fixas[k] || ajustar(base(i), est.tom, est.inten, est.clar); }
  function temaFinal() {
    var p = (PAL[est.paleta] && PAL[est.paleta].pagina) || PADRAO, t = {};
    ["papel", "tinta", "borda"].forEach(function (k) { t[k] = est.tema[k] || p[k]; });
    t.cinza = cinzaDe(t.tinta, t.papel);
    return t;
  }
  function aplicar() {
    P.comodos.forEach(function (c, i) { L.cor(i, final(i)); });
    var t = temaFinal(), r = document.documentElement.style;
    r.setProperty("--papel", t.papel); r.setProperty("--tinta", t.tinta); r.setProperty("--cinza", t.cinza); r.setProperty("--bronze", t.borda);
    L.fundo(); desenhar();
  }

  /* ---------- painel ---------- */
  var css = document.createElement("style");
  css.textContent = [
    ".pn{position:fixed;top:0;right:0;bottom:0;width:320px;overflow:auto;background:#fff;border-left:1px solid #e2ddd5;padding:24px;font:13px/1.5 Jost,system-ui,sans-serif;color:#1e1e1e;z-index:9}",
    "body{padding-right:320px}",
    ".pn h2{font-size:13px;font-weight:500;letter-spacing:.18em;text-transform:uppercase;margin:24px 0 8px}",
    ".pn h2:first-child{margin-top:0}",
    ".pn .ch{display:flex;align-items:center;gap:8px;width:100%;padding:8px;border:1px solid #e2ddd5;border-radius:4px;background:#fff;cursor:pointer;margin-bottom:4px;font:inherit;color:inherit;text-align:left}",
    ".pn .ch[aria-pressed=true]{border-color:#1e1e1e}",
    ".pn .sw{display:flex;gap:2px}.pn .sw i{width:16px;height:16px;border-radius:2px}",
    ".pn .duo{display:flex;gap:4px}.pn .duo button{flex:1}",
    ".pn label{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:4px 0}",
    ".pn input[type=range]{width:100%}",
    ".pn .reg{display:flex;justify-content:space-between;color:#67625b;margin-top:-4px}",
    ".pn input[type=color]{width:40px;height:24px;border:1px solid #e2ddd5;padding:0;background:none}",
    ".pn .acao{display:flex;gap:8px;margin-top:24px}.pn .acao button{flex:1;padding:12px;border-radius:4px;font:inherit;font-weight:500;cursor:pointer}",
    ".pn .sal{background:#fff;border:1px solid #1e1e1e;color:#1e1e1e}.pn .con{background:#1e1e1e;border:1px solid #1e1e1e;color:#fff}",
    ".pn .st{color:#67625b;margin-top:8px;min-height:20px}",
    "@media (max-width:760px){.pn{top:auto;width:auto;left:0;max-height:50vh;border-left:0;border-top:1px solid #e2ddd5}body{padding-right:0;padding-bottom:50vh}}"
  ].join("");
  document.head.appendChild(css);
  var pn = document.createElement("aside"); pn.className = "pn"; pn.setAttribute("aria-label", "Painel de cor");
  document.body.appendChild(pn);

  function botao(txt, fn, pressionado) {
    var b = document.createElement("button"); b.className = "ch"; b.type = "button";
    b.setAttribute("aria-pressed", pressionado ? "true" : "false"); b.innerHTML = txt; b.onclick = fn; return b;
  }
  function regua(rot, min, max, passo, val, esq, dir, fn) {
    var w = document.createElement("div");
    w.innerHTML = '<label>' + rot + '</label><input type="range" min="' + min + '" max="' + max + '" step="' + passo + '" value="' + val + '"><div class="reg"><span>' + esq + '</span><span>' + dir + '</span></div>';
    w.querySelector("input").oninput = function () { fn(+this.value); aplicar(); };
    return w;
  }
  function seletor(rot, val, fn) {
    var l = document.createElement("label"); l.innerHTML = "<span>" + rot + '</span><input type="color" value="' + val.toLowerCase() + '">';
    l.querySelector("input").oninput = function () { fn(this.value.toUpperCase()); aplicar(); };
    return l;
  }
  function desenhar() {
    pn.innerHTML = "";
    var h = function (t) { var e = document.createElement("h2"); e.textContent = t; pn.appendChild(e); };
    h("Paleta");
    var nomes = (temPiso ? ["piso"] : []).concat(Object.keys(PAL));
    nomes.forEach(function (k) {
      var cores = k === "piso" ? P.comodos.map(function (c) { return c.piso; }).filter(Boolean).slice(0, 6) : PAL[k].cores;
      var sw = '<span class="sw">' + cores.map(function (c) { return '<i style="background:' + c + '"></i>'; }).join("") + "</span>";
      pn.appendChild(botao(sw + (k === "piso" ? "Do piso" : PAL[k].nome), function () { est.paleta = k; est.fixas = {}; est.tema = {}; aplicar(); }, est.paleta === k));
    });
    h("Pintar por");
    var duo = document.createElement("div"); duo.className = "duo";
    duo.appendChild(botao("Ambiente", function () { est.modo = "ambiente"; est.fixas = {}; aplicar(); }, est.modo === "ambiente"));
    duo.appendChild(botao("Setor", function () { est.modo = "setor"; est.fixas = {}; aplicar(); }, est.modo === "setor"));
    pn.appendChild(duo);
    h("Tom");
    pn.appendChild(regua("Temperatura", -1, 1, .05, est.tom, "mais frio", "mais quente", function (v) { est.tom = v; }));
    pn.appendChild(regua("Intensidade", .4, 1.6, .05, est.inten, "mais suave", "mais viva", function (v) { est.inten = v; }));
    pn.appendChild(regua("Claridade", -.15, .15, .01, est.clar, "mais escura", "mais clara", function (v) { est.clar = v; }));
    h(est.modo === "setor" ? "Setores" : "Ambientes");
    var vistos = {};
    P.comodos.forEach(function (c, i) {
      var k = chave(i); if (vistos[k]) return; vistos[k] = 1;
      pn.appendChild(seletor(est.modo === "setor" ? NOME_SETOR[k] || k : c.nome, final(i), function (v) { est.fixas[k] = v; }));
    });
    h("Página");
    var t = temaFinal();
    pn.appendChild(seletor("Fundo", t.papel, function (v) { est.tema.papel = v; }));
    pn.appendChild(seletor("Texto", t.tinta, function (v) { est.tema.tinta = v; }));
    pn.appendChild(seletor("Borda", t.borda, function (v) { est.tema.borda = v; }));
    var tl = document.createElement("label"); tl.innerHTML = '<span>Ver todos acesos</span><input type="checkbox"' + (est.todos ? " checked" : "") + ">";
    tl.querySelector("input").onchange = function () { est.todos = this.checked; L.todos(est.todos); };
    pn.appendChild(tl);
    var ac = document.createElement("div"); ac.className = "acao";
    ac.innerHTML = '<button class="sal" type="button">Salvar</button><button class="con" type="button">Concluir</button>';
    ac.querySelector(".sal").onclick = function () { enviar("/salvar"); };
    ac.querySelector(".con").onclick = function () { enviar("/concluir"); };
    pn.appendChild(ac);
    var st = document.createElement("p"); st.className = "st"; st.id = "pn-st"; pn.appendChild(st);
  }
  function enviar(rota) {
    var st = document.getElementById("pn-st");
    fetch(rota, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cores: P.comodos.map(function (c, i) { return final(i); }), tema: temaFinal(), paleta: est.paleta, modo: est.modo }) })
      .then(function (r) { return r.json(); })
      .then(function () { st.textContent = rota === "/concluir" ? "Pronto. Pode fechar esta aba." : "Salvo na página."; })
      .catch(function () { st.textContent = "Não salvou. O painel ainda está aberto no Claude?"; });
  }

  fetch("/__paletas.json").then(function (r) { return r.json(); }).then(function (j) {
    Object.keys(j).forEach(function (k) { if (k.charAt(0) !== "_") PAL[k] = j[k]; });
    if (!PAL[est.paleta]) est.paleta = "paleta1";
    // o que ja estava salvo e diferente da paleta vira cor fixa, pra reabrir igual
    P.comodos.forEach(function (c, i) { var k = chave(i); if (!est.fixas[k] && c.cor.toUpperCase() !== final(i)) est.fixas[k] = c.cor.toUpperCase(); });
    est.todos = true; L.todos(true);
    aplicar();
  });
})();
