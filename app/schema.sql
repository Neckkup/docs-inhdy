-- ใช้ร่วมกันระหว่างเว็บแอป (app/main.py) และ worker (worker/worker.py)
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
  id         INTEGER PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,
  pw_hash    TEXT NOT NULL,
  is_admin   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- หนึ่งแถวต่อซับโดเมน (sites/<name>/) ที่สร้างผ่านเว็บ
CREATE TABLE IF NOT EXISTS projects (
  name       TEXT PRIMARY KEY,
  title      TEXT,
  kind       TEXT,              -- slides | design | docs | html
  format     TEXT,              -- รูปแบบที่เลือกตอนเผยแพร่
  source_url TEXT,
  owner_id   INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- queued -> running -> (review -> approved -> running) -> done | failed | cancelled
CREATE TABLE IF NOT EXISTS jobs (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id),
  action     TEXT NOT NULL,     -- publish | delete
  name       TEXT NOT NULL,
  source_url TEXT,
  format     TEXT,
  status     TEXT NOT NULL DEFAULT 'queued',
  kind       TEXT,
  title      TEXT,
  warnings   TEXT,              -- JSON list
  log        TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
