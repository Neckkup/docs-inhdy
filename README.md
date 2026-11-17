# docs.inhdy.com

เว็บเอกสารสาธารณะ — หนึ่งโปรเจกต์ต่อหนึ่งซับโดเมน (`<ชื่อ>.docs.inhdy.com`)
รันด้วย nginx หลัง Traefik บนเครื่องนี้ HTTPS ออกให้อัตโนมัติ

> ทุกอย่างใน `sites/` เปิดให้ทุกคนดูได้ อย่าวางไฟล์ลับหรือข้อมูลภายใน

## เว็บจัดการ — https://docs.app.inhdy.com

login แล้ววางลิงก์ `https://claude.ai/artifact/…` → เลือกซับโดเมน → เลือกรูปแบบ → กดเผยแพร่
หน้าเดียวกันแสดงเอกสารทั้งหมด (ค้นหาได้) งานล่าสุด และปุ่มอัปเดต/ลบของโปรเจกต์ที่เป็นเจ้าของ

| รูปแบบ | ใช้กับ | ผลลัพธ์ |
|---|---|---|
| อัตโนมัติ | ทุกประเภท | เลือกให้ตามประเภทด้านล่าง |
| สไลด์ (อ่าน + นำเสนอ) | Slides | สไลด์เรียงลงมา กด P นำเสนอ |
| สไลด์ (โหมดนำเสนอ) | Slides | เปิดมาเป็นสไลด์ทีละหน้า |
| Canvas | Design | canvas เลื่อน/ซูม แท็บตาม page |
| หน้าจอเรียงลงมา | Design | ทุกหน้าจอในหน้าเดียว อ่านบนมือถือได้ |
| หน้าเอกสาร | Docs | ทุกแท็บรวมหน้าเดียว มีสารบัญ |
| ตามต้นฉบับ | HTML | วางไฟล์ตรง |
| ให้ AI จัดหน้าใหม่ | ทุกประเภท | ส่งเนื้อหาให้โมเดลผ่าน LiteLLM เรียบเรียงเป็นหน้าเว็บ (ต้องตั้ง `LITELLM_*` ใน `.env`) |

ระบบสแกนไฟล์ก่อนขึ้นเว็บ: เจอ key/token/รหัสผ่าน → หยุดรอเจ้าของงานกด "เผยแพร่ต่อ" หรือ "ยกเลิก"
ของเดิมที่ถูกทับหรือลบจะย้ายไป `data/trash/` (เก็บ 30 วัน)

### ติดตั้งครั้งแรก

```bash
./deploy.sh                                           # สร้าง .env (APP_SECRET) + build เว็บจัดการ
docker compose exec docs-app python manage.py adduser <ชื่อ> --admin
mkdir -p ~/.config/systemd/user && cp worker/docs-worker.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now docs-worker
sudo loginctl enable-linger $USER                     # ให้ worker ทำงานต่อหลัง logout
```

AI (ไม่บังคับ): สร้าง virtual key ใน LiteLLM แล้วใส่ `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `LITELLM_MODEL`
ใน `.env` (ดู `.env.example`) จากนั้น `./deploy.sh` และ `systemctl --user restart docs-worker`

ผู้ใช้: `docker compose exec docs-app python manage.py adduser|passwd|deluser|list …` (ไม่มีหน้าสมัครเอง)

### ทำงานอย่างไร

```
เบราว์เซอร์ ─▶ docs-app (FastAPI, container) ─▶ data/app.db (คิวงาน, SQLite)
                                                   │
             worker/worker.py (host, systemd) ◀────┘
               1. claude -p  — เครื่องมืออ่านอย่างเดียว (Artifact, Claude Docs read/export)
                  ใช้บัญชี claude.ai ที่ login ไว้บนเครื่องนี้ → ไฟล์ลง data/jobs/<id>/raw
               2. ตรวจประเภท → tools/*.py แปลงตามรูปแบบ (AI → LiteLLM)
               3. สแกนข้อมูลลับ → ย้ายเข้า sites/<ชื่อ>/ → ./deploy.sh
```

> ทุกคนที่ login ได้ สั่งดึง artifact ใดก็ได้ที่บัญชี claude.ai บนเครื่องนี้เปิดได้ — สร้างบัญชีให้เฉพาะคนที่ไว้ใจ

## ใช้งานแบบไม่ผ่านเว็บ

| ต้องการ | ทำ |
|---|---|
| สร้างโปรเจกต์ใหม่ (หน้า canvas) | `./new-project.sh <ชื่อ> "ชื่อที่แสดง"` |
| แก้เอกสาร | แก้ไฟล์ใน `sites/<ชื่อ>/` — เว็บเปลี่ยนทันที |
| เพิ่มหน้า | สร้าง `.html` ใน `sites/<ชื่อ>/` แล้วเพิ่ม `{ "file": "x.html", "title": "…" }` ใน `canvas.json` |
| ลบโปรเจกต์ | ลบ `sites/<ชื่อ>/` แล้ว `./deploy.sh` |
| เอา Artifact จาก claude.ai ขึ้นเว็บ | ใน Claude Code: `/publish-artifact <ลิงก์> <ชื่อ>` |

ชื่อโปรเจกต์ใช้ได้แค่ `a-z 0-9 -`

## Artifact ที่รองรับ

| ประเภท | ผลลัพธ์ | ตัวแปลง |
|---|---|---|
| Slides | หน้าเดียว โหมดอ่าน + โหมดนำเสนอ (กด P) ตัดโน้ตผู้บรรยายออก | `tools/slides2html.py` |
| Design (canvas) | canvas เลื่อน/ซูมได้, แท็บตาม page, หน้าจอละไฟล์, โหมดมืด | `tools/design2html.py` + `tools/dc-lite.js` |
| HTML ธรรมดา | วางตรง (ฟีเจอร์ `window.claude.*` จะใช้ไม่ได้) | — |
| Claude Docs | หน้าเอกสารรวมทุกแท็บ (ผ่านเว็บ: export อัตโนมัติ) | `tools/md2html.py` |

ขั้นตอนเต็มอยู่ใน `.claude/skills/publish-artifact/SKILL.md`

## โครงสร้าง

```
app/               เว็บจัดการ (FastAPI): login, ฟอร์มเผยแพร่, รายการเอกสาร
  schema.sql         ตาราง users / projects / jobs (ใช้ร่วมกับ worker)
  common.py          ชื่อซับโดเมน, รูปแบบผลลัพธ์ (ใช้ร่วมกับ worker)
  manage.py          จัดการผู้ใช้
worker/            worker.py (คิวงาน: ดึง→แปลง→สแกน→deploy) + systemd unit
data/              app.db, ไฟล์ชั่วคราวของงาน, ถังขยะ (ไม่อยู่ใน git)
.env               APP_SECRET, LITELLM_* (ไม่อยู่ใน git — ดู .env.example)
deploy.sh          สร้าง compose.yml + หน้ารวมจาก sites/ แล้ว deploy
new-project.sh     สร้างโปรเจกต์ใหม่ + deploy
nginx.conf         ซับโดเมน -> sites/<ชื่อ>/
compose.yml        สร้างโดย deploy.sh — อย่าแก้มือ
sites/_root/       หน้า docs.inhdy.com (สร้างอัตโนมัติ)
sites/<ชื่อ>/      เนื้อหาแต่ละโปรเจกต์
templates/canvas/  หน้าตั้งต้นของโปรเจกต์ใหม่
  index.html         canvas viewer (อ่าน canvas.json) — ใช้ร่วมกับ Design จาก claude.ai
  canvas.json        รายการหน้า + ตำแหน่ง (ไม่ใส่ x/y = จัดเรียงให้)
  assets/page.css    สไตล์ร่วมของทุกหน้า (สว่าง/มืด)
  welcome.html       หน้าตัวอย่าง
  guide.html         วิธีเพิ่มหน้า (ลบได้)
tools/             ตัวแปลง artifact (slides2html, design2html, screens, md2html) + test harness (jsdom)
```

DNS: `docs.inhdy.com` และ `*.docs.inhdy.com` ชี้มาที่เครื่องนี้แล้ว — โปรเจกต์ใหม่ไม่ต้องตั้ง DNS เพิ่ม
