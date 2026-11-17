"""จัดการผู้ใช้ (ไม่มีหน้าสมัครสมาชิก — แอดมินสร้างให้)

  docker compose exec docs-app python manage.py adduser <ชื่อ> [--admin]
  docker compose exec docs-app python manage.py passwd <ชื่อ>
  docker compose exec docs-app python manage.py deluser <ชื่อ>
  docker compose exec docs-app python manage.py list
"""
import getpass
import sys

from main import NAME_RE_USER, db, hash_password  # noqa: F401  (main ตรวจ APP_SECRET + สร้างตาราง)


def ask_pw() -> str:
    pw = getpass.getpass("รหัสผ่าน: ")
    if len(pw) < 10:
        sys.exit("รหัสผ่านต้องยาวอย่างน้อย 10 ตัว")
    if pw != getpass.getpass("ยืนยันรหัสผ่าน: "):
        sys.exit("รหัสผ่านไม่ตรงกัน")
    return pw


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]
    with db() as con:
        if cmd == "list":
            for u in con.execute("SELECT username, is_admin, created_at FROM users ORDER BY id"):
                print(f"{u['username']:20} {'admin' if u['is_admin'] else '':6} {u['created_at']}")
            return
        if not args:
            sys.exit(__doc__)
        name = args[0].strip().lower()
        if cmd == "adduser":
            if not NAME_RE_USER.match(name):
                sys.exit("ชื่อผู้ใช้: a-z 0-9 . _ - ยาว 2-32 ตัว")
            if con.execute("SELECT 1 FROM users WHERE username = ?", (name,)).fetchone():
                sys.exit("มีผู้ใช้นี้แล้ว")
            con.execute("INSERT INTO users (username, pw_hash, is_admin) VALUES (?, ?, ?)",
                        (name, hash_password(ask_pw()), int("--admin" in args)))
            print(f"สร้าง {name} แล้ว")
        elif cmd == "passwd":
            n = con.execute("UPDATE users SET pw_hash = ? WHERE username = ?",
                            (hash_password(ask_pw()), name)).rowcount
            print("เปลี่ยนแล้ว (session เก่าหลุดหมด)" if n else "ไม่พบผู้ใช้")
        elif cmd == "deluser":
            con.execute("UPDATE projects SET owner_id = NULL WHERE owner_id = "
                        "(SELECT id FROM users WHERE username = ?)", (name,))
            con.execute("DELETE FROM jobs WHERE user_id = (SELECT id FROM users WHERE username = ?)", (name,))
            n = con.execute("DELETE FROM users WHERE username = ?", (name,)).rowcount
            print("ลบแล้ว" if n else "ไม่พบผู้ใช้")
        else:
            sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
