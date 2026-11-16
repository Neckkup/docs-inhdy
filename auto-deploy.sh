#!/usr/bin/env bash
# deploy อัตโนมัติ: ดึงจาก GitHub ถ้ามี commit ใหม่ก็รัน deploy.sh ให้
#   ./auto-deploy.sh                    เช็กหนึ่งรอบ (systemd timer เรียกทุก 1 นาที)
#   sudo ./auto-deploy.sh --install     ติดตั้ง systemd timer
#   sudo ./auto-deploy.sh --uninstall   ถอนการติดตั้ง
#   ดู log: journalctl -u docs-auto-deploy -f
# ตั้ง branch ที่จะติดตาม: BRANCH=main (ค่าเริ่มต้น)
set -euo pipefail
cd "$(dirname "$0")"

BRANCH=${BRANCH:-main}
UNIT=docs-auto-deploy
# ไฟล์ที่ deploy.sh สร้างใหม่ทุกครั้ง — คืนค่าก่อน pull จะได้ไม่ชนกับใน git
GENERATED=(compose.yml sites/_root/index.html)

case ${1:-} in
  --install)
    [[ $EUID -eq 0 ]] || { echo "ต้องรันด้วย sudo" >&2; exit 1; }
    owner=$(stat -c %U .)
    cat > /etc/systemd/system/$UNIT.service <<EOF
[Unit]
Description=docs.inhdy.com: pull จาก GitHub แล้ว deploy ถ้ามีของใหม่
After=network-online.target docker.service

[Service]
Type=oneshot
User=$owner
WorkingDirectory=$PWD
Environment=BRANCH=$BRANCH
ExecStart=$PWD/auto-deploy.sh
EOF
    cat > /etc/systemd/system/$UNIT.timer <<EOF
[Unit]
Description=เช็ก docs.inhdy.com ทุก 1 นาที

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF
    systemctl daemon-reload
    systemctl enable --now $UNIT.timer
    echo "ติดตั้งแล้ว: เช็ก origin/$BRANCH ทุก 1 นาที ในนามผู้ใช้ $owner"
    echo "ดู log: journalctl -u $UNIT -f"
    exit 0 ;;
  --uninstall)
    [[ $EUID -eq 0 ]] || { echo "ต้องรันด้วย sudo" >&2; exit 1; }
    systemctl disable --now $UNIT.timer 2>/dev/null || true
    rm -f /etc/systemd/system/$UNIT.service /etc/systemd/system/$UNIT.timer
    systemctl daemon-reload
    echo "ถอนแล้ว"
    exit 0 ;;
  "") ;;
  *) echo "ใช้: $0 [--install|--uninstall]" >&2; exit 1 ;;
esac

# กันรันซ้อนกัน (deploy.sh อาจรอเช็ก HTTPS นานเกิน 1 นาที)
exec 9>.git/auto-deploy.lock
flock -n 9 || exit 0

current=$(git symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")
if [[ $current != "$BRANCH" ]]; then
  echo "อยู่บน branch '$current' ไม่ใช่ '$BRANCH' — ข้าม" >&2
  exit 1
fi

git fetch -q origin "$BRANCH"
old=$(git rev-parse HEAD)
new=$(git rev-parse FETCH_HEAD)
[[ $old == "$new" ]] && exit 0

git checkout -q -- "${GENERATED[@]}" 2>/dev/null || true
if ! git merge -q --ff-only FETCH_HEAD; then
  echo "pull ไม่ได้: บนเครื่องนี้มีไฟล์ที่แก้ค้างไว้ หรือประวัติแยกจาก origin/$BRANCH" >&2
  git status --short >&2
  exit 1
fi

echo "อัปเดต ${old:0:7} -> ${new:0:7}"
git log --oneline "$old..$new"
./deploy.sh
