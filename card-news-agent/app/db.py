import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id                       TEXT PRIMARY KEY,
    topic_id                 TEXT NOT NULL,
    status                   TEXT NOT NULL,
    stage                    TEXT NOT NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL,
    research_session_id      TEXT,
    storyboard_session_id    TEXT,
    candidates_json          TEXT,
    selected_candidates_json TEXT,
    verification_json        TEXT,
    revision_notes_json      TEXT NOT NULL DEFAULT '[]',
    error_message            TEXT,
    retry_count               INTEGER NOT NULL DEFAULT 0
);
"""

# Stage 2에서 추가된 컬럼. 기존 Stage 1 테스트 데이터를 보존하기 위해 CREATE TABLE을
# 바꾸는 대신 마이그레이션으로 추가한다 — "duplicate column" 오류는 이미 적용된
# 마이그레이션이라는 뜻이므로 무시한다.
MIGRATIONS = [
    "ALTER TABLE runs ADD COLUMN images_json TEXT",
    "ALTER TABLE runs ADD COLUMN source_text TEXT",
    "ALTER TABLE runs ADD COLUMN source_url TEXT",
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(SCHEMA)
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
        # 서버 재시작 안전장치: 이전 프로세스가 죽으면서 running으로 남은 런은
        # 아무도 진행시키지 않으므로 즉시 failed로 정리한다 (고아 상태 방지).
        conn.execute(
            "UPDATE runs SET status='failed', error_message='interrupted by restart', "
            "updated_at=? WHERE status='running'",
            (_now(),),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_run(
    topic_id: str,
    status: str,
    stage: str,
    source_text: str | None = None,
    source_url: str | None = None,
) -> str:
    run_id = str(uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, topic_id, status, stage, created_at, updated_at, source_text, source_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, topic_id, status, stage, now, now, source_text, source_url),
        )
    return run_id


def get_run(run_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    for key in (
        "candidates_json",
        "selected_candidates_json",
        "verification_json",
        "revision_notes_json",
        "images_json",
    ):
        if d.get(key):
            d[key.removesuffix("_json")] = json.loads(d[key])
        else:
            d[key.removesuffix("_json")] = None
    return d


def update_run(run_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with _connect() as conn:
        conn.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))


def require_stage(run_id: str, status: str, stage: str) -> dict:
    row = get_run(run_id)
    if row is None:
        raise LookupError(f"run not found: {run_id}")
    if row["status"] != status or row["stage"] != stage:
        raise ValueError(
            f"run {run_id} is at status={row['status']!r} stage={row['stage']!r}, "
            f"expected status={status!r} stage={stage!r}"
        )
    return row
