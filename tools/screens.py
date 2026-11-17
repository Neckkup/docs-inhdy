#!/usr/bin/env python3
"""เปลี่ยนผลลัพธ์ของ design2html.py เป็นมุมมอง "หน้าจอเรียงลงมา" (แทน canvas)

ใช้:  python3 tools/screens.py <โฟลเดอร์ที่ design2html สร้างแล้ว>

เขียนทับ index.html: ทุก artboard เรียงลงมาในหน้าเดียว แต่ละอันเป็น iframe ย่อให้พอดีความกว้างจอ
แยกตาม page ของ canvas, มีลิงก์เปิดหน้าจอเดี่ยว — ไฟล์ <Board>.html และ canvas.json ไม่ถูกแก้
"""
import html
import json
import sys
from pathlib import Path


def main(site: Path) -> None:
    data = json.loads((site / "canvas.json").read_text(encoding="utf-8"))
    pages = {p["id"]: p.get("name") or "" for p in data.get("pages") or []}
    groups: dict = {}
    for b in data["boards"]:
        groups.setdefault(b.get("page"), []).append(b)

    parts = []
    for pid, boards in groups.items():
        if pid in pages and len(groups) > 1:
            parts.append(f'<h2 class="page">{html.escape(pages[pid])}</h2>')
        for b in boards:
            f = html.escape(b["file"], quote=True)
            parts.append(
                f'<figure class="screen" data-w="{int(b.get("w") or 1440)}" data-h="{int(b.get("h") or 1000)}">'
                f'<figcaption><span>{html.escape(b["title"])}</span><a href="{f}" target="_blank">เปิดเต็มจอ ↗</a></figcaption>'
                f'<div class="frame"><iframe src="{f}" loading="lazy" title="{html.escape(b["title"], quote=True)}"></iframe></div>'
                f'</figure>')

    title = html.escape(data.get("title") or "Design")
    (site / "index.html").write_text(TEMPLATE.format(title=title, body="\n".join(parts)), encoding="utf-8")
    print(f"{site}/index.html  ({len(data['boards'])} หน้าจอ)")


TEMPLATE = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#f5f5f4; --fg:#1c1917; --muted:#78716c; --card:#fff; --accent:#2563eb; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --card:#292524; --accent:#60a5fa; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 system-ui,-apple-system,"Noto Sans Thai",sans-serif; }}
main {{ max-width:1280px; margin:0 auto; padding:32px 16px 80px; }}
h1 {{ margin:0 0 24px; font-size:1.8rem; }}
h2.page {{ margin:48px 0 16px; font-size:1.3rem; color:var(--muted); }}
.screen {{ margin:0 0 32px; }}
figcaption {{ display:flex; justify-content:space-between; gap:12px; margin-bottom:8px; font-weight:600; }}
figcaption a {{ color:var(--accent); font-weight:400; text-decoration:none; white-space:nowrap; }}
.frame {{ position:relative; overflow:hidden; border-radius:10px; background:var(--card);
          box-shadow:0 2px 16px rgba(0,0,0,.12); }}
.frame iframe {{ position:absolute; top:0; left:0; border:0; transform-origin:0 0; }}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
{body}
</main>
<script>
(() => {{
  const fit = () => document.querySelectorAll('.screen').forEach(s => {{
    const w = +s.dataset.w, h = +s.dataset.h, box = s.querySelector('.frame'), f = box.firstElementChild;
    const k = Math.min(1, box.parentElement.clientWidth / w);
    f.style.width = w + 'px'; f.style.height = h + 'px'; f.style.transform = 'scale(' + k + ')';
    box.style.height = (h * k) + 'px';
  }});
  addEventListener('resize', fit); fit();
}})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
