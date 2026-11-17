#!/usr/bin/env python3
"""แปลง Markdown (เช่น export จาก Claude Docs) เป็นหน้าเอกสาร HTML หน้าเดียว — stdlib เท่านั้น

ใช้:  python3 tools/md2html.py <ชื่อเรื่อง> <ไฟล์ปลายทาง.html> <แท็บ1.md> [แท็บ2.md ...]

- หลายไฟล์ = หลายแท็บ รวมในหน้าเดียว มีสารบัญด้านข้าง
- HTML ดิบใน markdown ถูก escape ทั้งหมด (ไม่รันสคริปต์ใด ๆ จากเนื้อหา)
- รองรับ: หัวข้อ, ย่อหน้า, ตัวหนา/เอียง/ขีดฆ่า, `code`, code block, ลิงก์, รูป, รายการ (ซ้อนได้),
  checklist, blockquote, ตาราง GFM, เส้นคั่น
"""
import html
import re
import sys
from pathlib import Path

SAFE_URL = re.compile(r"^(https?://|mailto:|#|/|\./|[A-Za-z0-9._-]+(/|$))", re.I)


def _url(u: str) -> str:
    u = u.strip().strip("<>")
    return html.escape(u, quote=True) if SAFE_URL.match(u) else "#"


def inline(s: str) -> str:
    codes: list[str] = []

    def keep_code(m):
        codes.append(f"<code>{html.escape(m.group(2))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"(`+)(.+?)\1", keep_code, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)",
               lambda m: f'<img src="{_url(html.unescape(m.group(2)))}" alt="{m.group(1)}" loading="lazy">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)",
               lambda m: f'<a href="{_url(html.unescape(m.group(2)))}">{m.group(1)}</a>', s)
    s = re.sub(r"&lt;(https?://[^\s&]+)&gt;", lambda m: f'<a href="{_url(m.group(1))}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)|(?<![_\w])_(?!\s)(.+?)(?<!\s)_(?![_\w])",
               lambda m: f"<em>{m.group(1) or m.group(2)}</em>", s)
    s = re.sub(r"~~(.+?)~~", r"<del>\1</del>", s)
    s = re.sub(r"  \n|\\\n", "<br>\n", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)


def slug(text: str, used: set) -> str:
    base = re.sub(r"[^\w฀-๿-]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-") or "h"
    s, n = base, 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def _is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", line))


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def blocks(lines: list[str], toc: list, used: set, prefix: str) -> str:
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if m := re.match(r"^\s*(```+|~~~+)\s*([\w+-]*)", line):
            fence, lang, body = m.group(1), m.group(2), []
            i += 1
            while i < n and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body))}</code></pre>")
            continue
        if m := re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line):
            lvl, txt = len(m.group(1)), inline(m.group(2))
            hid = slug(f"{prefix}-{m.group(2)}" if prefix else m.group(2), used)
            if lvl <= 3:
                toc.append((lvl, hid, re.sub(r"<[^>]+>", "", txt)))
            out.append(f'<h{lvl} id="{hid}">{txt}</h{lvl}>')
            i += 1
            continue
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        if line.lstrip().startswith(">"):
            body = []
            while i < n and lines[i].lstrip().startswith(">"):
                body.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{blocks(body, [], used, prefix)}</blockquote>")
            continue
        if "|" in line and i + 1 < n and _is_table_sep(lines[i + 1]):
            head = _cells(line)
            aligns = []
            for c in _cells(lines[i + 1]):
                aligns.append("center" if c.startswith(":") and c.endswith(":") else
                              "right" if c.endswith(":") else "left" if c.startswith(":") else "")
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_cells(lines[i]))
                i += 1

            def td(tag, c, k):
                a = aligns[k] if k < len(aligns) and aligns[k] else ""
                st = f' style="text-align:{a}"' if a else ""
                return f"<{tag}{st}>{inline(c)}</{tag}>"
            th = "".join(td("th", c, k) for k, c in enumerate(head))
            tb = "".join("<tr>" + "".join(td("td", c, k) for k, c in enumerate(r)) + "</tr>" for r in rows)
            out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
            continue
        if LIST_RE.match(line):
            html_list, i = _list(lines, i, toc, used, prefix)
            out.append(html_list)
            continue
        para = []
        while i < n and lines[i].strip() and not (
                re.match(r"^(#{1,6})\s", lines[i]) or re.match(r"^\s*(```|~~~)", lines[i])
                or lines[i].lstrip().startswith(">") or LIST_RE.match(lines[i])
                or ("|" in lines[i] and i + 1 < n and _is_table_sep(lines[i + 1]))):
            para.append(lines[i] if lines[i].endswith("  ") else lines[i].strip())
            i += 1
        out.append(f"<p>{inline(chr(10).join(para))}</p>")
    return "\n".join(out)


def _list(lines, i, toc, used, prefix):
    m = LIST_RE.match(lines[i])
    indent = len(m.group(1).expandtabs(4))
    ordered = m.group(2)[0].isdigit()
    tag = "ol" if ordered else "ul"
    start = int(re.match(r"\d+", m.group(2)).group()) if ordered else 1
    items = []
    n = len(lines)
    while i < n:
        m = LIST_RE.match(lines[i])
        if not m or len(m.group(1).expandtabs(4)) != indent or m.group(2)[0].isdigit() != ordered:
            break
        body = [m.group(3)]
        i += 1
        while i < n:
            ln = lines[i]
            if not ln.strip():
                # บรรทัดว่างภายในรายการ: ต่อเมื่อบรรทัดถัดไปยังเยื้องอยู่
                if i + 1 < n and len(lines[i + 1]) - len(lines[i + 1].lstrip()) > indent:
                    body.append("")
                    i += 1
                    continue
                break
            lead = len(ln.expandtabs(4)) - len(ln.expandtabs(4).lstrip())
            if lead <= indent and (LIST_RE.match(ln) or not body[-1].strip()):
                break
            if lead <= indent and not LIST_RE.match(ln):
                body.append(ln.strip())   # lazy continuation
            else:
                body.append(ln.expandtabs(4)[min(lead, indent + 2):] if lead > indent else ln)
            i += 1
        first, rest = body[0], body[1:]
        check = ""
        if cm := re.match(r"^\[([ xX])\]\s+(.*)", first):
            check = '<input type="checkbox" disabled{}> '.format(" checked" if cm.group(1) != " " else "")
            first = cm.group(2)
        nested = blocks(rest, toc, used, prefix) if any(r.strip() for r in rest) else ""
        items.append(f"<li>{check}{inline(first)}{nested}</li>")
    st = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{st}>" + "".join(items) + f"</{tag}>", i


def render_tabs(title: str, tabs: list[tuple[str, str]]) -> str:
    used: set = set()
    sections, nav = [], []
    multi = len(tabs) > 1
    for k, (name, md) in enumerate(tabs):
        toc: list = []
        lines = md.replace("\r\n", "\n").split("\n")
        # หัว H1 ซ้ำกับชื่อเรื่องในแท็บแรก — ตัดออก (ใช้ <h1> ของหน้าแทน)
        if k == 0 and lines and re.match(r"^#\s+", lines[0]):
            lines = lines[1:]
        body = blocks(lines, toc, used, f"t{k}" if multi else "")
        sid = slug(name, used) if multi else "content"
        head = f'<h2 class="tab-title" id="{sid}">{html.escape(name)}</h2>' if multi else ""
        sections.append(f'<section class="tab">{head}{body}</section>')
        sub = "".join(f'<li class="l{lvl}"><a href="#{hid}">{html.escape(t)}</a></li>'
                      for lvl, hid, t in toc if lvl >= 2 or not multi)
        if multi:
            nav.append(f'<li class="tab-link"><a href="#{sid}">{html.escape(name)}</a>'
                       + (f"<ul>{sub}</ul>" if sub else "") + "</li>")
        else:
            nav.append(sub)
    return TEMPLATE.format(title=html.escape(title), nav="".join(nav), body="\n".join(sections))


TEMPLATE = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src * data:; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com">
<title>{title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,400;0,600;0,700;1,400&display=swap">
<style>
:root {{ --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --line:#e7e5e4; --accent:#2563eb; --code:#f5f5f4; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --line:#44403c; --accent:#60a5fa; --code:#292524; }}
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; scroll-padding-top:16px; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:17px/1.75 Sarabun,system-ui,sans-serif; }}
.wrap {{ display:grid; grid-template-columns:260px minmax(0,1fr); gap:48px; max-width:1180px; margin:0 auto; padding:40px 24px 96px; }}
nav {{ position:sticky; top:24px; align-self:start; max-height:calc(100vh - 48px); overflow:auto; font-size:.9rem; }}
nav ul {{ list-style:none; margin:0; padding:0; }}
nav ul ul {{ padding-left:12px; border-left:1px solid var(--line); margin:4px 0 10px; }}
nav li.l3 {{ padding-left:12px; }}
nav a {{ color:var(--muted); text-decoration:none; display:block; padding:3px 0; }}
nav a:hover {{ color:var(--accent); }}
nav .tab-link > a {{ color:var(--fg); font-weight:600; }}
article {{ min-width:0; }}
h1 {{ font-size:2.2rem; line-height:1.25; margin:0 0 24px; }}
h2 {{ font-size:1.5rem; margin:2em 0 .5em; padding-bottom:.25em; border-bottom:1px solid var(--line); }}
h2.tab-title {{ font-size:1.9rem; border:0; margin-top:2.2em; color:var(--accent); }}
section.tab:first-child h2.tab-title {{ margin-top:0; }}
h3 {{ font-size:1.2rem; margin:1.6em 0 .4em; }}
a {{ color:var(--accent); }}
code {{ background:var(--code); padding:.1em .35em; border-radius:4px; font-size:.88em; }}
pre {{ background:var(--code); padding:14px 16px; border-radius:8px; overflow:auto; line-height:1.5; }}
pre code {{ background:none; padding:0; }}
blockquote {{ margin:1em 0; padding:.2em 1em; border-left:3px solid var(--accent); color:var(--muted); }}
.table {{ overflow-x:auto; margin:1em 0; }}
table {{ border-collapse:collapse; min-width:100%; font-size:.95rem; }}
th, td {{ border:1px solid var(--line); padding:8px 12px; vertical-align:top; text-align:left; }}
th {{ background:var(--code); }}
img {{ max-width:100%; height:auto; }}
hr {{ border:0; border-top:1px solid var(--line); margin:2em 0; }}
li > input[type=checkbox] {{ margin-right:6px; }}
@media (max-width:860px) {{
  .wrap {{ grid-template-columns:1fr; gap:16px; padding:24px 16px 64px; }}
  nav {{ position:static; max-height:none; border-bottom:1px solid var(--line); padding-bottom:12px; }}
}}
@media print {{ nav {{ display:none; }} .wrap {{ display:block; }} }}
</style>
</head>
<body>
<div class="wrap">
<nav aria-label="สารบัญ"><ul>{nav}</ul></nav>
<article>
<h1>{title}</h1>
{body}
</article>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    title, out, files = sys.argv[1], Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]
    tabs = [(f.stem, f.read_text(encoding="utf-8")) for f in files]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_tabs(title, tabs), encoding="utf-8")
    print(out)
