---
name: publish-artifact
description: เผยแพร่ Artifact จาก claude.ai (Slides, Design/canvas, HTML, Docs) ขึ้น https://<ชื่อ>.docs.inhdy.com ใช้เมื่อผู้ใช้ส่งลิงก์ claude.ai/artifact/... แล้วขอให้ deploy, เผยแพร่, ขึ้นโดเมน, หรืออัปเดตโปรเจกต์ที่เคยดึงมา
argument-hint: <ลิงก์ artifact> [ชื่อโปรเจกต์]
---

# Publish artifact → docs.inhdy.com

อินพุต: `$ARGUMENTS` = ลิงก์ artifact และชื่อโปรเจกต์ (ถ้าไม่ให้ชื่อ ให้เสนอชื่อจากหัวข้อ artifact
แล้วถามยืนยันก่อน) ชื่อต้องเป็น `a-z 0-9 -` เพราะจะเป็นซับโดเมน

ทุกอย่างใน `sites/` เป็น **สาธารณะ** — ก่อน deploy ต้องดูเนื้อหาก่อนเสมอ

## 1. ตรวจประเภท

`Artifact` action `list`, scope `files`, url = ลิงก์ แล้วดูจากไฟล์:

| เจอไฟล์ | ประเภท | ไปขั้น |
|---|---|---|
| `project/deck.json` | Slides | 2A |
| `project/canvas.json` | Design (canvas) | 2B |
| type "Docs" (มี `SKILL.md` + `artifact-type/…` แต่ไม่มี `project/`) | Claude Docs | 2C |
| มีแค่ `index.html` (+ ไฟล์ประกอบ) ไม่มี `artifact-type/` | HTML ธรรมดา | 2D |

ที่เก็บไฟล์ดิบ: `<scratchpad>/import/<ชื่อ>/` (ใช้ `out_dir` ของ Artifact read — ไฟล์ลงดิสก์ตรง ห้ามพิมพ์เนื้อหาใหม่เอง)

## 2A. Slides

1. read `paths`: `project/deck.json`, ไฟล์ใน `format.shared` (ปกติ `project/deck.css`), และ `project/slides/<id>.html` ทุก id ใน `order`
2. `python3 -I tools/slides2html.py <scratch>/import/<ชื่อ> sites/<ชื่อ>/index.html`
3. สคริปต์ตัด `<aside>` (โน้ตผู้บรรยาย) ให้แล้ว — ยืนยัน: `grep -c '<aside' sites/<ชื่อ>/index.html` ต้องได้ 0
4. ถ้าสไลด์มีรูปจาก asset store / ไฟล์ใน `project/` ที่ไม่ใช่ html/css ให้ดึงมาด้วยและแก้ path

## 2B. Design (canvas)

1. read `paths`: `project/canvas.json` และทุกไฟล์ใน `boards`
2. เช็กว่าใช้ฟีเจอร์ที่ `tools/dc-lite.js` ไม่รองรับไหม: `grep -l '<dc-import' <scratch>/import/<ชื่อ>/project/*.dc.html`
   ถ้าเจอ → ต้องเพิ่มการรองรับใน dc-lite.js ก่อน (หรือบอกผู้ใช้)
3. `python3 -I tools/design2html.py <scratch>/import/<ชื่อ> sites/<ชื่อ>`
   ได้: `index.html` (viewer เดียวกับ `templates/canvas/`), `canvas.json`, `<Board>.html` ต่อหน้าจอ
   ทดสอบ viewer: เหมือนข้อ 4 แต่ใช้ `canvas.mjs` แทน `render.mjs`
4. ทดสอบ render (เครื่องนี้ไม่มี node/browser — ใช้ container):
   ```bash
   docker run --rm -v $PWD/tools/test:/t:ro -v $PWD/sites/<ชื่อ>:/site:ro node:22-alpine \
     sh -c "cd /tmp && npm i --silent jsdom@25 >/dev/null 2>&1 && cp /t/render.mjs . && node render.mjs"
   ```
   (ติดตั้ง jsdom ใน /tmp ของ container — อย่า mount แบบเขียนได้ ไม่งั้นได้ node_modules ของ root ค้างในโปรเจกต์)
   ต้องได้ `leftover{{}}=0` และ `errors=0` ทุกหน้า ทั้ง dark=0 และ dark=1

## 2C. Claude Docs

export ของ Docs connector คืนไฟล์เป็น base64 ในผลลัพธ์เท่านั้น (ไม่ลงดิสก์) — **ห้ามพิมพ์ base64 ใหม่เอง**
ทางเลือก บอกผู้ใช้ให้เลือก:
- ผู้ใช้กด Export → Markdown ในเมนู doc แล้ววางไฟล์ใน `<scratch>/import/<ชื่อ>/` → แปลงเป็น HTML
- อ่าน doc ด้วย Docs `read` แล้วเขียนหน้า HTML ใหม่จากเนื้อหา (ช้า เหมาะกับ doc สั้น)
Docs มักมีแท็บภายใน (ความปลอดภัย, คำถามเปิด) — ถามว่าจะเผยแพร่แท็บไหน

## 2D. HTML ธรรมดา

1. read `paths`: `index.html` และไฟล์ประกอบที่ list เจอ → `sites/<ชื่อ>/` ตาม path เดิม
2. `grep -n 'window.claude' sites/<ชื่อ>/*.html` — ถ้าเจอ แปลว่าใช้ capability ของ claude.ai
   (db, ask Claude, user ฯลฯ) ซึ่งจะไม่ทำงานนอก claude.ai → แจ้งผู้ใช้ว่าส่วนไหนจะใช้ไม่ได้

## 3. ตรวจเนื้อหาก่อนเผยแพร่

อ่านเนื้อหาที่จะขึ้น แล้วแจ้งผู้ใช้ถ้าเจอ: ชื่อ/ข้อมูลคนจริง, ข้อมูลภายใน, โน้ตถึงทีม, key/token/URL ภายใน
ถ้าไม่แน่ใจ ถามก่อน deploy

## 4. Deploy และยืนยัน

ถ้ารันใน Claude Code บน cloud (ไม่มี docker/เซิร์ฟเวอร์): commit + push แทน — เมื่อเข้า `main`
แล้ว `auto-deploy.sh` บนเซิร์ฟเวอร์จะ pull + deploy ให้เองภายใน ~1 นาที บอกผู้ใช้ว่าต้อง merge เข้า `main`

บนเซิร์ฟเวอร์:

```bash
./deploy.sh            # สร้าง router + ใบรับรองให้ซับโดเมนใหม่ แล้วเช็ก HTTP ให้
```
อัปเดตโปรเจกต์ที่มีอยู่แล้ว (โฟลเดอร์ใน sites/ มีอยู่แล้ว) ไม่ต้องรัน deploy.sh — ไฟล์เปลี่ยนทันที

แจ้งผู้ใช้: URL, ประเภทที่ตรวจเจอ, อะไรถูกตัดออก (โน้ต/แท็บ), อะไรใช้ไม่ได้นอก claude.ai,
และสิ่งที่ยังไม่ได้ตรวจ (เครื่องนี้ไม่มีเบราว์เซอร์ — หน้าตาจริงต้องให้ผู้ใช้เปิดดู)
