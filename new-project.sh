#!/usr/bin/env bash
# ใช้: ./new-project.sh <ชื่อ> ["ชื่อที่แสดง"]
#   คัดลอก templates/canvas/ ไปที่ sites/<ชื่อ>/ แล้ว deploy ไปที่ https://<ชื่อ>.docs.inhdy.com
set -euo pipefail
cd "$(dirname "$0")"

name=${1:-}
title=${2:-$name}
if [[ ! $name =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "ใช้: $0 <ชื่อ> [\"ชื่อที่แสดง\"]   (ชื่อใช้ได้แค่ a-z 0-9 และ -)" >&2
  exit 1
fi
if [[ -e sites/$name ]]; then
  echo "มี sites/$name อยู่แล้ว" >&2
  exit 1
fi

cp -r templates/canvas "sites/$name"
python3 -I - "sites/$name" "$title" <<'EOF'
import html, json, sys
from pathlib import Path
root, title = Path(sys.argv[1]), sys.argv[2]
for f in root.rglob("*"):
    if f.suffix == ".html":
        f.write_text(f.read_text(encoding="utf-8").replace("__TITLE__", html.escape(title)), encoding="utf-8")
    elif f.suffix == ".json":
        f.write_text(f.read_text(encoding="utf-8").replace('"__TITLE__"', json.dumps(title, ensure_ascii=False)), encoding="utf-8")
EOF

./deploy.sh
