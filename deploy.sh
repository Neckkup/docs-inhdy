#!/usr/bin/env bash
# สร้าง compose.yml + หน้ารวมจากโฟลเดอร์ใน sites/ แล้ว deploy
#   sites/<project>/   ->  https://<project>.docs.inhdy.com
#   sites/_root/       ->  https://docs.inhdy.com  (สร้างอัตโนมัติ ห้ามแก้มือ)
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN=docs.inhdy.com
ALT_DOMAIN=docs.app.inhdy.com
RESOLVER=inhdy-public

projects=()
for d in sites/*/; do
  name=$(basename "$d")
  [[ $name == _* ]] && continue
  if [[ ! $name =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    echo "ข้าม '$name': ชื่อต้องเป็น a-z 0-9 และ - เท่านั้น" >&2
    continue
  fi
  projects+=("$name")
done

router() { # name rule
  cat <<EOF
      - traefik.http.routers.$1.rule=$2
      - traefik.http.routers.$1.entrypoints=websecure
      - traefik.http.routers.$1.tls=true
      - traefik.http.routers.$1.tls.certresolver=$RESOLVER
      - traefik.http.routers.$1.service=docs
EOF
}

# ---------- compose.yml ----------
{
  cat <<'EOF'
# ไฟล์นี้สร้างโดย deploy.sh — อย่าแก้มือ
services:
  docs:
    image: nginx:1.27-alpine
    container_name: docs
    restart: unless-stopped
    volumes:
      - ./sites:/srv/sites:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks: [public]
    labels:
      - traefik.enable=true
      - traefik.docker.network=public
      - traefik.http.services.docs.loadbalancer.server.port=80
EOF
  router docs-main "Host(\`$DOMAIN\`)"
  router docs-app "Host(\`$ALT_DOMAIN\`)"
  # หนึ่ง router ต่อโปรเจกต์ = ใบรับรองแยกกัน โปรเจกต์ไหนพังไม่กระทบตัวอื่น
  for p in "${projects[@]}"; do
    router "docs-p-$p" "Host(\`$p.$DOMAIN\`)"
  done
  cat <<'EOF'

networks:
  public:
    external: true
EOF
} > compose.yml

# ---------- หน้ารวม sites/_root/index.html ----------
esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }
items=""
for p in "${projects[@]}"; do
  title=$(grep -o -m1 '<title>[^<]*</title>' "sites/$p/index.html" 2>/dev/null | sed 's/<[^>]*>//g' || true)
  title=$(printf '%s' "${title:-$p}" | esc)
  items+="      <li><a href=\"https://$p.$DOMAIN/\"><span>$title</span><small>$p.$DOMAIN</small></a></li>"$'\n'
done
[[ -z $items ]] && items='      <li class="empty">ยังไม่มีโปรเจกต์</li>'$'\n'

mkdir -p sites/_root
cat > sites/_root/index.html <<EOF
<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>เอกสาร</title>
  <style>
    :root { --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --line:#e7e5e4; --accent:#2563eb; }
    @media (prefers-color-scheme: dark) {
      :root { --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --line:#44403c; --accent:#60a5fa; }
    }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--fg);
           font:16px/1.7 system-ui,-apple-system,"Noto Sans Thai",sans-serif; }
    main { max-width:760px; margin:0 auto; padding:48px 16px; }
    h1 { margin:0 0 4px; font-size:2rem; }
    p.lead { margin:0 0 32px; color:var(--muted); }
    ul { list-style:none; padding:0; margin:0; border-top:1px solid var(--line); }
    li { border-bottom:1px solid var(--line); }
    li.empty { padding:14px 0; color:var(--muted); }
    a { display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap;
        padding:14px 0; color:var(--accent); text-decoration:none; }
    a:hover span { text-decoration:underline; }
    small { color:var(--muted); }
  </style>
</head>
<body>
  <main>
    <h1>เอกสาร</h1>
    <p class="lead">เอกสารของทุกโปรเจกต์</p>
    <ul>
$items    </ul>
  </main>
</body>
</html>
EOF

# ---------- deploy ----------
docker compose up -d --remove-orphans
docker exec docs nginx -s reload >/dev/null 2>&1 || true

echo
echo "https://$DOMAIN/"
for p in "${projects[@]}"; do
  code=000
  for _ in $(seq 1 12); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "https://$p.$DOMAIN/" 2>/dev/null || true)
    [[ $code == 200 ]] && break
    sleep 5
  done
  echo "https://$p.$DOMAIN/  ->  HTTP $code"
done
