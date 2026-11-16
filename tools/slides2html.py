#!/usr/bin/env python3
"""แปลง Claude Slides ที่ดึงมาแล้ว (project/deck.json + slides/*.html) เป็นเว็บหน้าเดียว

ใช้:  python3 tools/slides2html.py <โฟลเดอร์ที่มี project/> <ไฟล์ปลายทาง.html>

- เรียงสไลด์ตาม deck.json "order"
- ตัด <aside> (โน้ตผู้บรรยาย) ออก ไม่ให้หลุดไปหน้าสาธารณะ
- โหมดอ่าน: สไลด์เรียงลงมา ย่อให้พอดีจอ (ใช้บนมือถือได้)
- โหมดนำเสนอ: กด P หรือปุ่ม ▶ — ลูกศร/Space เลื่อน, Esc ออก
"""
import html
import json
import re
import sys
from pathlib import Path

W, H = 1920, 1080


def main(src: Path, out: Path) -> None:
    proj = src / "project"
    deck = json.loads((proj / "deck.json").read_text(encoding="utf-8"))
    css = "\n".join(
        (src / p).read_text(encoding="utf-8")
        for p in deck.get("format", {}).get("shared", [])
    )
    fonts = "\n".join(
        f'<link rel="stylesheet" href="{html.escape(f["href"])}">'
        for f in deck.get("faces", {}).values()
        if f.get("href", "").startswith("https://fonts.googleapis.com/")
    )

    slides = []
    for sid in deck["order"]:
        body = (proj / "slides" / f"{sid}.html").read_text(encoding="utf-8")
        body = re.sub(r"<aside\b.*?</aside>", "", body, flags=re.S | re.I)
        slides.append(f'<div class="frame"><div class="slide">{body.strip()}</div></div>')

    title = html.escape(deck.get("title", "Slides"))
    page = TEMPLATE.format(
        title=title, fonts=fonts, css=css, w=W, h=H,
        slides="\n".join(slides), count=len(slides),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{out}  ({len(slides)} สไลด์)")


TEMPLATE = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<style>
/* ---- deck.css ---- */
{css}
/* ---- viewer ---- */
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: #2b2f36; }}
body {{ font-family: 'Sarabun', Tahoma, sans-serif; }}
.slide p, .slide h1, .slide h2, .slide h3, .slide ul {{ margin: 0; }}
.slide table {{ border-collapse: collapse; }}
.slide th, .slide td {{ padding: 16px 20px; text-align: left; vertical-align: top; }}
.slide x-shape {{ display: block; }}
.slide x-shape[kind="arrow-right"] {{ clip-path: polygon(0 30%, 60% 30%, 60% 0, 100% 50%, 60% 100%, 60% 70%, 0 70%); }}

.bar {{ position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 12px;
        padding: 10px 16px; background: #1f2228; color: #e8eaed; font: 15px/1.4 system-ui, sans-serif; }}
.bar .t {{ flex: 1; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.bar button {{ font: inherit; color: #1f2228; background: #e8eaed; border: 0; border-radius: 6px;
               padding: 6px 14px; cursor: pointer; }}
.deck {{ max-width: 1280px; margin: 0 auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }}
.frame {{ position: relative; width: 100%; aspect-ratio: {w} / {h}; overflow: hidden;
          border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,.35); }}
.slide {{ position: absolute; top: 0; left: 0; width: {w}px; height: {h}px; transform-origin: 0 0; }}
.slide > section {{ width: 100%; height: 100%; }}

body.present {{ overflow: hidden; background: #000; }}
body.present .bar {{ display: none; }}
body.present .deck {{ max-width: none; padding: 0; }}
body.present .frame {{ display: none; position: fixed; inset: 0; margin: auto; border-radius: 0;
                        box-shadow: none; width: min(100vw, calc(100vh * {w} / {h})); }}
body.present .frame.on {{ display: block; }}
.count {{ position: fixed; right: 16px; bottom: 12px; z-index: 3; display: none;
          color: rgba(255,255,255,.6); font: 14px system-ui, sans-serif; }}
body.present .count {{ display: block; }}
@media (prefers-reduced-motion: reduce) {{ .slide * {{ animation: none !important; }} }}
</style>
</head>
<body>
<div class="bar"><span class="t">{title}</span><span>{count} สไลด์</span><button id="play" title="นำเสนอ (P)">▶ นำเสนอ</button></div>
<main class="deck">
{slides}
</main>
<div class="count" id="count"></div>
<script>
(() => {{
  const frames = [...document.querySelectorAll('.frame')];
  const count = document.getElementById('count');
  let i = 0;
  const fit = () => frames.forEach(f => {{
    const s = f.firstElementChild;
    if (f.offsetWidth) s.style.transform = 'scale(' + f.offsetWidth / {w} + ')';
  }});
  const show = n => {{
    i = Math.max(0, Math.min(frames.length - 1, n));
    frames.forEach((f, k) => f.classList.toggle('on', k === i));
    count.textContent = (i + 1) + ' / ' + frames.length;
    fit();
  }};
  const start = () => {{
    const top = frames.findIndex(f => f.getBoundingClientRect().bottom > 60);
    document.body.classList.add('present'); show(top < 0 ? 0 : top);
    document.documentElement.requestFullscreen?.().catch(() => {{}});
  }};
  const stop = () => {{
    document.body.classList.remove('present'); frames.forEach(f => f.classList.remove('on'));
    fit(); frames[i].scrollIntoView({{ block: 'center' }});
    if (document.fullscreenElement) document.exitFullscreen?.();
  }};
  document.getElementById('play').onclick = start;
  document.addEventListener('keydown', e => {{
    const on = document.body.classList.contains('present');
    if (!on) {{ if (e.key === 'p' || e.key === 'P') start(); return; }}
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(e.key)) {{ e.preventDefault(); show(i + 1); }}
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(e.key)) {{ e.preventDefault(); show(i - 1); }}
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(frames.length - 1);
    else if (e.key === 'Escape') stop();
  }});
  document.addEventListener('click', e => {{
    if (!document.body.classList.contains('present')) return;
    show(i + (e.clientX > innerWidth / 3 ? 1 : -1));
  }});
  document.addEventListener('fullscreenchange', () => {{
    if (!document.fullscreenElement && document.body.classList.contains('present')) stop();
  }});
  addEventListener('resize', fit);
  fit();
}})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
