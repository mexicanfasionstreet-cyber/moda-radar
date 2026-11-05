# -*- coding: utf-8 -*-
"""Plantilla y estilos del panel de moda-radar (sin dependencias)."""

import html as _html

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#0a0a0c; --bg2:#0f0f13; --surface:#14141a; --surface-2:#1a1a22;
  --line:#26262f; --line-2:#33333f;
  --text:#ece9e4; --muted:#9a9aa6; --dim:#6e6e7a;
  --accent:#ff4d6d; --accent-2:#c9ff4a; --radius:14px;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,ui-serif,serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
}
html{scroll-behavior:smooth}
body{
  margin:0; background:radial-gradient(1200px 600px at 50% -300px,#1b1220 0%,transparent 70%),var(--bg);
  color:var(--text); font-family:var(--sans); font-size:16px; line-height:1.45;
  -webkit-font-smoothing:antialiased;
}
a{color:inherit; text-decoration:none}
img{display:block; max-width:100%}
.wrap{max-width:1360px; margin:0 auto; padding:0 22px}

/* ---------- header ---------- */
header.top{padding:30px 0 18px; border-bottom:1px solid var(--line)}
.top-row{display:flex; align-items:flex-end; justify-content:space-between; gap:20px; flex-wrap:wrap}
.wordmark{display:flex; align-items:baseline; gap:12px}
.wordmark h1{
  font-family:var(--serif); font-weight:600; font-size:clamp(26px,4vw,40px);
  letter-spacing:.14em; margin:0; text-transform:uppercase;
}
.wordmark h1 em{font-style:normal; color:var(--accent)}
.tagline{margin:6px 0 0; color:var(--muted); font-size:13.5px; letter-spacing:.02em}
.kpis{display:flex; gap:26px; text-align:right}
.kpi b{display:block; font-family:var(--serif); font-size:24px; font-weight:600; line-height:1}
.kpi span{font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--dim)}

/* ---------- controles ---------- */
.controls{
  position:sticky; top:0; z-index:40; backdrop-filter:blur(14px);
  background:rgba(10,10,12,.86); border-bottom:1px solid var(--line);
}
.controls-in{display:flex; gap:14px; align-items:center; padding:12px 0; flex-wrap:wrap}
.chips{display:flex; gap:7px; overflow-x:auto; scrollbar-width:none; flex:1 1 auto; padding:2px}
.chips::-webkit-scrollbar{display:none}
.chip{
  border:1px solid var(--line-2); background:transparent; color:var(--muted);
  font:inherit; font-size:12.5px; letter-spacing:.03em; padding:7px 13px; border-radius:999px;
  cursor:pointer; white-space:nowrap; transition:.15s;
}
.chip:hover{border-color:var(--muted); color:var(--text)}
.chip.on{background:var(--text); border-color:var(--text); color:#0a0a0c; font-weight:600}
.chip.trade-toggle{border-style:dashed}
.chip.trade-toggle.on{background:var(--accent); border-color:var(--accent); border-style:solid; color:#12100f}
.chip .n{opacity:.55; margin-left:5px; font-variant-numeric:tabular-nums}
.search{position:relative; flex:0 0 260px}
.search input{
  width:100%; background:var(--surface); border:1px solid var(--line-2); border-radius:999px;
  color:var(--text); font:inherit; font-size:13.5px; padding:9px 14px 9px 34px; outline:none;
}
.search input:focus{border-color:var(--accent)}
.search svg{position:absolute; left:12px; top:50%; transform:translateY(-50%); opacity:.5}
select.src{
  background:var(--surface); border:1px solid var(--line-2); border-radius:999px;
  color:var(--muted); font:inherit; font-size:12.5px; padding:8px 12px; max-width:190px; cursor:pointer;
}

/* ---------- hero ---------- */
.hero{padding:30px 0 6px}
.hero h2, section h2.block{
  font-family:var(--serif); font-size:15px; font-weight:600; letter-spacing:.18em;
  text-transform:uppercase; color:var(--muted); margin:0 0 16px; display:flex; align-items:center; gap:12px;
}
h2.block::after{content:""; flex:1; height:1px; background:var(--line)}
.hero-grid{display:grid; grid-template-columns:1.55fr 1fr; gap:16px}
@media(max-width:880px){.hero-grid{grid-template-columns:1fr}}
.lead{position:relative; border-radius:var(--radius); overflow:hidden; min-height:340px; display:flex; align-items:flex-end; background:var(--surface)}
.lead img{position:absolute; inset:0; width:100%; height:100%; object-fit:cover; opacity:.72}
.lead .shade{position:absolute; inset:0; background:linear-gradient(180deg,rgba(10,10,12,.05) 25%,rgba(10,10,12,.95) 100%)}
.lead .txt{position:relative; padding:24px; width:100%}
.lead h3{font-family:var(--serif); font-size:clamp(21px,2.4vw,30px); line-height:1.18; margin:0 0 8px; font-weight:600}
.lead p{margin:0; color:#c8c5c0; font-size:14px; max-width:56ch}
.sec-col{display:flex; flex-direction:column; gap:16px}
.sec-col .card{margin:0}
.eyebrow{display:flex; gap:8px; align-items:center; font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-2); margin-bottom:9px}

/* ---------- tarjetas ---------- */
section.sec{padding:34px 0 0}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:16px}
.card{
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  overflow:hidden; display:flex; flex-direction:column; transition:border-color .18s, transform .18s;
}
.card:hover{border-color:var(--line-2); transform:translateY(-2px)}
.thumb{position:relative; display:block; aspect-ratio:16/9; background:var(--surface-2); overflow:hidden}
.thumb img{width:100%; height:100%; object-fit:cover; transition:transform .4s ease}
.card:hover .thumb img{transform:scale(1.04)}
.thumb.noimg{display:grid; place-items:center}
.thumb.noimg span{font-family:var(--serif); font-size:38px; color:var(--line-2); letter-spacing:.06em}
.src-badge{
  position:absolute; left:10px; bottom:10px; background:rgba(10,10,12,.82);
  backdrop-filter:blur(6px); border:1px solid rgba(255,255,255,.12);
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; padding:4px 9px; border-radius:6px; color:#fff;
}
.card .body{padding:14px 16px 16px; display:flex; flex-direction:column; gap:8px; flex:1}
.card h3{font-family:var(--serif); font-size:16.5px; line-height:1.28; margin:0; font-weight:600}
.card h3 a:hover{color:var(--accent)}
.card p{margin:0; font-size:13px; color:var(--muted); line-height:1.5}
.card .meta{margin-top:auto; display:flex; align-items:center; gap:9px; font-size:11px; color:var(--dim); letter-spacing:.02em; flex-wrap:wrap}
.card .meta .sep{width:3px; height:3px; border-radius:50%; background:var(--dim)}
.tag{color:var(--dim); border:1px solid var(--line); padding:1px 7px; border-radius:999px; font-size:10px; text-transform:uppercase; letter-spacing:.08em}

/* ---------- varios ---------- */
.empty{padding:70px 0; text-align:center; color:var(--dim); font-family:var(--serif); font-size:18px}
footer{margin-top:60px; border-top:1px solid var(--line); padding:26px 0 44px; color:var(--dim); font-size:12.5px}
footer a{color:var(--muted); border-bottom:1px solid var(--line-2)}
footer .row{display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap}
.const{display:none!important}
#count{font-variant-numeric:tabular-nums}
@media(max-width:640px){
  .kpis .kpi:nth-child(3){display:none}
  .search{flex:1 1 100%; order:3}
  .lead{min-height:260px}
}
"""

JS = """
(function(){
  var cards=[].slice.call(document.querySelectorAll('[data-card]'));
  var sections=[].slice.call(document.querySelectorAll('section.sec'));
  var chips=[].slice.call(document.querySelectorAll('.chip[data-cat]'));
  var tradeBtn=document.getElementById('only-trade');
  var input=document.getElementById('q');
  var sel=document.getElementById('src');
  var count=document.getElementById('count');
  var empty=document.getElementById('empty');
  var state={cat:'todo',q:'',src:'',trade:false};

  function rel(ts){
    var d=new Date(ts); if(isNaN(d)) return '';
    var s=(Date.now()-d.getTime())/1000;
    if(s<3600) return 'hace '+Math.max(1,Math.round(s/60))+' min';
    if(s<86400){var h=Math.round(s/3600); return 'hace '+h+' h';}
    var dd=Math.round(s/86400);
    if(dd===1) return 'ayer';
    if(dd<7) return 'hace '+dd+' días';
    return d.toLocaleDateString('es-ES',{day:'numeric',month:'short'});
  }
  cards.forEach(function(c){var t=c.querySelector('time'); if(t&&t.dataset.ts) t.textContent=rel(t.dataset.ts);});

  function apply(){
    var q=state.q.trim().toLowerCase(), n=0;
    cards.forEach(function(c){
      var okCat = state.cat==='todo' || (' '+c.dataset.cat+' ').indexOf(' '+state.cat+' ')>-1;
      var okSrc = !state.src || c.dataset.src===state.src;
      var okQ = !q || (c.dataset.text||'').toLowerCase().indexOf(q)>-1;
      var okKind = !state.trade || c.dataset.kind==='trade';
      var vis = okCat && okSrc && okQ && okKind;
      c.classList.toggle('const',!vis); if(vis) n++;
    });
    sections.forEach(function(s){
      s.classList.toggle('const', !s.querySelector('[data-card]:not(.const)'));
    });
    var hero=document.querySelector('.hero');
    if(hero) hero.classList.toggle('const', !hero.querySelector('[data-card]:not(.const)'));
    if(count) count.textContent=n;
    if(empty) empty.classList.toggle('const', n>0);
    chips.forEach(function(ch){ ch.classList.toggle('on', ch.dataset.cat===state.cat); });
  }

  chips.forEach(function(ch){ ch.addEventListener('click',function(){ state.cat=ch.dataset.cat; apply(); }); });
  if(tradeBtn){ tradeBtn.addEventListener('click',function(){ state.trade=!state.trade; tradeBtn.classList.toggle('on',state.trade); apply(); }); }
  if(input){ input.addEventListener('input',function(){ state.q=input.value; apply(); }); }
  if(sel){ sel.addEventListener('change',function(){ state.src=sel.value; apply(); }); }
  document.addEventListener('keydown',function(e){
    if(e.key==='/'&&document.activeElement!==input){ e.preventDefault(); input&&input.focus(); }
    if(e.key==='Escape'&&document.activeElement===input){ input.value=''; state.q=''; apply(); input.blur(); }
  });
  apply();
})();
"""


CAT_LABEL = {}


def esc(s):
    return _html.escape(str(s or ""), quote=True)


def safe_url(u):
    u = (u or "").strip()
    if u.startswith("http://") or u.startswith("https://") or u.startswith("/"):
        return u.replace('"', "%22").replace("<", "%3C").replace(">", "%3E")
    return ""


def _monogram(source):
    letters = "".join(w[0] for w in source.split()[:2]).upper()
    return letters or "M"


def card_html(it):
    primary = it["tags"][0] if it["tags"] else ""
    tags = f'<span class="tag">{esc(CAT_LABEL.get(primary, ""))}</span>' if primary else ""
    img = safe_url(it.get("image"))
    if img:
        thumb = f'<img src="{esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
        thumb_cls = "thumb"
    else:
        thumb = f"<span>{esc(_monogram(it['source']))}</span>"
        thumb_cls = "thumb noimg"
    title = esc(it["title"])
    link = esc(safe_url(it["link"]))
    excerpt = esc(it["excerpt"])
    ts = esc(it["published"])
    return f"""<article class="card" data-card data-kind="{esc(it.get('kind', 'trade'))}" data-cat="{esc(' '.join(it['tags']))}" data-src="{esc(it['source'])}" data-ts="{ts}" data-text="{esc(it['title'] + ' ' + it['excerpt'] + ' ' + it['source'] + ' ' + ' '.join(it['tags']))}">
  <a class="{thumb_cls}" href="{link}" target="_blank" rel="noopener">{thumb}<span class="src-badge">{esc(it['source'])}</span></a>
  <div class="body">
    <h3><a href="{link}" target="_blank" rel="noopener">{title}</a></h3>
    <p>{excerpt}</p>
    <div class="meta"><time data-ts="{ts}">{ts[:10]}</time><span class="sep"></span>{tags}</div>
  </div>
</article>"""


def lead_html(it):
    img = safe_url(it.get("image"))
    pic = f'<img src="{esc(img)}" alt="" referrerpolicy="no-referrer">' if img else ""
    link = esc(safe_url(it["link"]))
    return f"""<a class="lead" href="{link}" target="_blank" rel="noopener" data-card data-kind="{esc(it.get('kind', 'trade'))}" data-cat="{esc(' '.join(it['tags']))}" data-src="{esc(it['source'])}" data-ts="{esc(it['published'])}" data-text="{esc(it['title'] + ' ' + it['excerpt'] + ' ' + it['source'])}">
  {pic}<span class="shade"></span>
  <div class="txt">
    <div class="eyebrow">{esc(it['source'])} · {esc(CAT_LABEL.get(it['tags'][0] if it['tags'] else '', ''))}</div>
    <h3>{esc(it['title'])}</h3>
    <p>{esc(it['excerpt'])}</p>
  </div>
</a>"""


def render(items, meta):
    CAT_LABEL.clear()
    CAT_LABEL.update({c["slug"]: c["label"] for c in meta["category_order"]})
    cats = [c for c in meta["category_order"] if any(c["slug"] in it["tags"] for it in items)]
    chips = [f'<button class="chip on" data-cat="todo">Todo<span class="n">{len(items)}</span></button>']
    for c in cats:
        n = sum(1 for it in items if c["slug"] in it["tags"])
        chips.append(f'<button class="chip" data-cat="{esc(c["slug"])}">{esc(c["label"])}<span class="n">{n}</span></button>')

    sources = sorted({it["source"] for it in items}, key=lambda s: s.lower())
    opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sources)

    hero = meta["hero"]
    hero_html = ""
    if hero:
        lead = lead_html(hero[0])
        rest = "".join(card_html(it) for it in hero[1:3])
        hero_html = f"""<div class="hero"><div class="wrap">
  <h2>Lo esencial</h2>
  <div class="hero-grid">{lead}<div class="sec-col">{rest}</div></div>
</div></div>"""
        hero_ids = {it["id"] for it in hero}
    else:
        hero_ids = set()

    blocks = []
    for c in cats:
        group = [it for it in items if c["slug"] in it["tags"] and it["id"] not in hero_ids]
        if not group:
            continue
        cards = "\n".join(card_html(it) for it in group)
        blocks.append(f"""<section class="sec" id="{esc(c['slug'])}"><div class="wrap">
  <h2 class="block">{esc(c['label'])} <span style="color:var(--dim);font-size:12px">({len(group)})</span></h2>
  <div class="grid">{cards}</div>
</div></section>""")

    updated = meta["generated_human"]
    first_date = meta["generated_date"]
    html_doc = TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS)
    html_doc = html_doc.replace("__CHIPS__", "".join(chips))
    html_doc = html_doc.replace("__OPTS__", opts)
    html_doc = html_doc.replace("__HERO__", hero_html)
    html_doc = html_doc.replace("__SECTIONS__", "\n".join(blocks))
    html_doc = html_doc.replace("__TOTAL__", str(len(items)))
    html_doc = html_doc.replace("__NSRC__", str(meta["sources_ok"]))
    html_doc = html_doc.replace("__UPDATED__", esc(updated))
    html_doc = html_doc.replace("__DATE__", esc(first_date))
    html_doc = html_doc.replace("__WINDOW__", str(meta["days"]))
    return html_doc


TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moda Radar · __DATE__</title>
<meta name="description" content="Radar diario de noticias de la industria de la moda: __TOTAL__ noticias de __NSRC__ fuentes.">
<style>__CSS__</style>
</head>
<body id="top">
<header class="top"><div class="wrap">
  <div class="top-row">
    <div class="wordmark">
      <div>
        <h1>Moda<em>/</em>Radar</h1>
        <p class="tagline">Industria de la moda · actualizado __UPDATED__ · ventana de __WINDOW__ días</p>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><b id="count">__TOTAL__</b><span>noticias</span></div>
      <div class="kpi"><b>__NSRC__</b><span>fuentes</span></div>
      <div class="kpi"><b>__DATE__</b><span>edición</span></div>
    </div>
  </div>
</div></header>

<div class="controls"><div class="wrap controls-in">
  <div class="chips">__CHIPS__<button class="chip trade-toggle" id="only-trade" title="Solo prensa especializada (BoF, WWD, Drapers, Retail Dive...)">Solo especializada</button></div>
  <div class="search">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="Buscar ( / )" autocomplete="off">
  </div>
  <select id="src" class="src"><option value="">Todas las fuentes</option>__OPTS__</select>
</div></div>

__HERO__
__SECTIONS__

<div class="wrap"><div id="empty" class="empty const">Nada coincide con esa búsqueda.</div></div>

<footer><div class="wrap row">
  <div>Generado automáticamente por <strong>moda-radar</strong> · sin edición humana · los enlaces llevan al medio original.</div>
  <div><a href="data/latest.json">datos en JSON</a> · <a href="#top">volver arriba</a></div>
</div></footer>
<script>__JS__</script>
</body>
</html>
"""
