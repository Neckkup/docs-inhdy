"""ค่าที่เว็บแอปและ worker ต้องตรงกัน (stdlib เท่านั้น — worker รันบนเครื่องโดยไม่มี pip)"""
import re

DOMAIN = "docs.inhdy.com"
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,40}[a-z0-9])?$")
# ซับโดเมนที่ห้ามใช้
RESERVED = {"www", "app", "api", "admin", "mail", "smtp", "ftp", "static", "assets", "root",
            "login", "auth", "docs", "status", "cdn", "ns1", "ns2"}
# claude.ai/artifact/<id> หรือ claude.ai/code/artifact/<uuid>
LINK_RE = re.compile(r"^https://claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]{8,64}/?$")

# รูปแบบผลลัพธ์: key -> (ชื่อที่แสดง, ใช้ได้กับ kind ไหน, คำอธิบาย)
FORMATS = {
    "auto":    ("อัตโนมัติ", {"slides", "design", "docs", "html"},
                "เลือกให้ตามประเภท: Slides → อ่าน+นำเสนอ, Design → canvas, Docs → หน้าเอกสาร, HTML → ตามต้นฉบับ"),
    "deck":    ("สไลด์ (อ่าน + นำเสนอ)", {"slides"}, "สไลด์เรียงลงมา กด P เพื่อนำเสนอ"),
    "present": ("สไลด์ (เปิดเป็นโหมดนำเสนอ)", {"slides"}, "เปิดมาเป็นสไลด์เต็มจอทีละหน้า"),
    "canvas":  ("Canvas เลื่อน/ซูม", {"design"}, "บอร์ดทั้งหมดบน canvas แท็บตาม page"),
    "screens": ("หน้าจอเรียงลงมา", {"design"}, "แต่ละหน้าจอเรียงต่อกันในหน้าเดียว อ่านง่ายบนมือถือ"),
    "doc":     ("หน้าเอกสาร", {"docs"}, "ทุกแท็บของ doc รวมในหน้าเดียว มีสารบัญ"),
    "asis":    ("ตามต้นฉบับ", {"html"}, "วางไฟล์ HTML ตรง ๆ"),
    "ai":      ("ให้ AI จัดหน้าใหม่", {"slides", "design", "docs", "html"},
                "ส่งเนื้อหาให้ AI (ผ่าน LiteLLM) เรียบเรียงเป็นหน้าเว็บอ่านง่ายหน้าเดียว"),
}
DEFAULT_FORMAT = {"slides": "deck", "design": "canvas", "docs": "doc", "html": "asis"}


def name_problem(name: str) -> str | None:
    if not NAME_RE.match(name or ""):
        return "ใช้ได้แค่ a-z 0-9 และ - (ห้ามขึ้นต้น/ลงท้ายด้วย -) ยาวไม่เกิน 42 ตัว"
    if name in RESERVED:
        return "ชื่อนี้สงวนไว้"
    return None
