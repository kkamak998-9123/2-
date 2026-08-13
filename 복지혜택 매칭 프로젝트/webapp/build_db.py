# -*- coding: utf-8 -*-
"""중앙부처 + 지자체 복지서비스 전체 목록을 SQLite(welfare.db)로 적재한다.

웹앱은 매 요청마다 공공데이터포털 API를 호출하는 대신 이 로컬 DB만 조회한다.
- 이유: API가 느리고 간헐적 타임아웃이 있어 Render 무료 플랜에서 실시간 프록시는
  불안정하다. 전체가 5천 건 미만으로 작아 한 번 적재해두면 조회가 즉각적이다.
- 상세(지원대상/선정기준/급여내용)는 클릭 시에만 API로 실시간 조회하므로 DB에
  담지 않는다(빌드 시간 단축 + 최신성).

DB가 없을 때 main.py가 이 스크립트를 별도 프로세스로 1회 실행한다.
전체 적재는 약 50회 내외의 API 호출로 보통 1~2분 걸린다.
"""

import os
import sqlite3
import sys

import welfare_api as w

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "welfare.db")


def build(db_path: str = DB_PATH) -> int:
    if not w.SERVICE_KEY:
        raise RuntimeError("WELFARE_API_KEY 환경변수를 설정해주세요.")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)

    con = sqlite3.connect(tmp)
    con.execute(
        "CREATE TABLE benefits ("
        "servId TEXT PRIMARY KEY, servNm TEXT, scope TEXT, jur TEXT, "
        "servDgst TEXT, servDtlLink TEXT, ctpvNm TEXT, sggNm TEXT, "
        "lifeArray TEXT, themaArray TEXT, trgterArray TEXT, "
        "onapPsbltYn TEXT, sprtCycNm TEXT, srvPvsnNm TEXT)"
    )

    def rows_from(iterator):
        for it in iterator:
            if not it.get("servId"):
                continue
            yield (
                it["servId"], it["servNm"], it["scope"], it["jur"],
                it["servDgst"], it["servDtlLink"], it["ctpvNm"], it["sggNm"],
                it["lifeArray"], it["themaArray"], it["trgterArray"],
                it["onapPsbltYn"], it["sprtCycNm"], it["srvPvsnNm"],
            )

    total = 0
    for iterator in (w.iter_national_all(), w.iter_local_all()):
        batch = list(rows_from(iterator))
        con.executemany(
            "INSERT OR IGNORE INTO benefits VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch,
        )
        total += len(batch)

    con.execute("CREATE INDEX idx_scope ON benefits(scope)")
    con.execute("CREATE INDEX idx_region ON benefits(ctpvNm, sggNm)")
    con.commit()
    con.close()
    os.replace(tmp, db_path)
    return total


if __name__ == "__main__":
    n = build(sys.argv[1] if len(sys.argv) > 1 else DB_PATH)
    print(f"welfare.db built: {n} benefits")
