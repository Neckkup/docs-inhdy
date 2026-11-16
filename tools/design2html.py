#!/usr/bin/env python3
"""แปลง Claude Design ที่ดึงมาแล้ว (project/canvas.json + *.dc.html) เป็นเว็บ

ใช้:  python3 tools/design2html.py <โฟลเดอร์ที่มี project/> <โฟลเดอร์ปลายทาง>

- แต่ละ artboard -> <ชื่อ>.html (ใช้ dc-lite.js แทน runtime ของ claude.ai)
- index.html = canvas viewer ตัวเดียวกับ templates/canvas/ (อ่าน canvas.json)
- ลิงก์ระหว่าง artboard (X.dc.html) ถูกแปลงเป็น X.html
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIEWER = HERE.parent / "templates" / "canvas" / "index.html"


def page_name(board: str) -> str:
    return re.sub(r"\.dc\.html$", ".html", board)


def main(src: Path, out: Path) -> None:
    proj = src / "project"
    canvas = json.loads((proj / "canvas.json").read_text(encoding="utf-8"))
    boards = canvas["boards"]
    order = canvas.get("order") or list(boards)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "dc-lite.js", out / "dc-lite.js")

    for b in order:
        text = (proj / b).read_text(encoding="utf-8")
        text = re.sub(r'<script src="\./support\.js"></script>', '<script src="./dc-lite.js"></script>', text)
        text = re.sub(r'(href=")([^"#:/]+)\.dc\.html', r"\1\2.html", text)
        if '<meta name="viewport"' not in text:
            text = text.replace('<meta charset="utf-8">',
                                '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">', 1)
        (out / page_name(b)).write_text(text, encoding="utf-8")

    title = canvas.get("title", "Design")
    data = {
        "title": title,
        "launch": (canvas.get("launch") or {}).get("page"),
        "pages": [{"id": p["id"], "name": p.get("name", "")} for p in canvas.get("pages") or []],
        "boards": [{"file": page_name(b), "title": boards[b].get("title") or b,
                    "x": boards[b].get("x", 0), "y": boards[b].get("y", 0),
                    "w": boards[b].get("w", 1440), "h": boards[b].get("h", 1000),
                    "page": boards[b].get("page")} for b in order],
        "notes": [{"text": n.get("text", ""), "x": n.get("x", 0), "y": n.get("y", 0),
                   "maxW": n.get("maxW"), "kind": n.get("kind", "title1"), "page": n.get("page")}
                  for n in (canvas.get("notes") or {}).values()],
    }
    (out / "canvas.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index.html").write_text(
        VIEWER.read_text(encoding="utf-8").replace("__TITLE__", html.escape(title)), encoding="utf-8")
    (out / "list.html").unlink(missing_ok=True)
    print(f"{out}/  ({len(order)} artboards)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
