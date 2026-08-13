"""조문 캐시용 sqlite 레이어."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "law_cache.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    article_no TEXT NOT NULL,       -- 조문번호 (예: 30)
    branch_no TEXT NOT NULL DEFAULT '',  -- 조문가지번호 (예: 2 -> 30-2)
    title TEXT,                     -- 조문제목
    raw_json TEXT NOT NULL,         -- 원본 조문단위 JSON (항/호/목 포함)
    law_mst TEXT,                   -- 법령일련번호
    fetched_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (article_no, branch_no)
);
"""


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def save_articles(items: list[dict], law_mst: str):
    conn = get_conn()
    with conn:
        for it in items:
            if it.get("조문여부") == "전문":
                continue  # 장/절 제목 등 실제 조문이 아닌 항목 제외
            conn.execute(
                """INSERT INTO articles (article_no, branch_no, title, raw_json, law_mst)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(article_no, branch_no) DO UPDATE SET
                     title=excluded.title, raw_json=excluded.raw_json,
                     law_mst=excluded.law_mst, fetched_at=datetime('now')""",
                (
                    it.get("조문번호", ""),
                    it.get("조문가지번호", ""),
                    it.get("조문제목", ""),
                    json.dumps(it, ensure_ascii=False),
                    law_mst,
                ),
            )
    conn.close()


def get_article(article_no: str, branch_no: str = "") -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT raw_json FROM articles WHERE article_no=? AND branch_no=?",
        (article_no, branch_no),
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def cache_is_empty() -> bool:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()
    return count == 0


def article_display_no(article_no: str, branch_no: str) -> str:
    return f"제{article_no}조" + (f"의{branch_no}" if branch_no else "")
