# docs.inhdy.com

เว็บเอกสารสาธารณะ — หนึ่งโปรเจกต์ต่อหนึ่งซับโดเมน (`<ชื่อ>.docs.inhdy.com`)
รันด้วย nginx หลัง Traefik บนเครื่องนี้ HTTPS ออกให้อัตโนมัติ

> ทุกอย่างใน `sites/` เปิดให้ทุกคนดูได้ อย่าวางไฟล์ลับหรือข้อมูลภายใน

## ใช้งาน

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
| Claude Docs | ต้อง Export → Markdown เองก่อน | — |

ขั้นตอนเต็มอยู่ใน `.claude/skills/publish-artifact/SKILL.md`

## โครงสร้าง

```
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
tools/             ตัวแปลง artifact + test harness (jsdom)
```

DNS: `docs.inhdy.com` และ `*.docs.inhdy.com` ชี้มาที่เครื่องนี้แล้ว — โปรเจกต์ใหม่ไม่ต้องตั้ง DNS เพิ่ม
