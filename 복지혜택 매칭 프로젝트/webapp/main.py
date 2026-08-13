# -*- coding: utf-8 -*-
"""복지혜택 매칭 웹앱 (FastAPI).

사용자 속성(나이·지역·관심주제·가구상황·키워드)을 받아, 미리 적재해둔
welfare.db(SQLite)에서 조건에 맞는 복지 혜택을 전국공통(중앙부처)/지역(지자체)으로
나눠 보여준다. 상세(지원대상/선정기준/급여내용)는 항목 클릭 시 공공데이터포털
API로 실시간 조회한다.
"""

import asyncio
import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import welfare_api as w
from codes import HOUSEHOLD_SITUATIONS, INTEREST_THEMES, life_stage_from_age

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "welfare.db"
BUILD_SCRIPT = BASE_DIR / "build_db.py"

RESULT_LIMIT = 200

app = FastAPI(title="복지혜택 매칭")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path in ("/", "/index.html", "/app.js", "/style.css"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


_DB_LOCK = asyncio.Lock()


def _query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


async def _ensure_db() -> None:
    """welfare.db가 없으면 build_db.py를 별도 프로세스로 실행해 적재한다(최초 1회)."""
    if DB_PATH.exists():
        return
    async with _DB_LOCK:
        if DB_PATH.exists():
            return
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(BUILD_SCRIPT), str(DB_PATH),
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0 or not DB_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail="복지 데이터 적재 실패: "
                + (err or b"").decode("utf-8", "replace")[-300:],
            )


@app.get("/api/options")
async def get_options():
    """프론트 폼에 필요한 선택지(관심주제·가구상황·지역)를 제공한다."""
    await _ensure_db()
    ctpv_rows = _query(
        "SELECT DISTINCT ctpvNm FROM benefits "
        "WHERE scope='local' AND ctpvNm<>'' ORDER BY ctpvNm"
    )
    sgg_rows = _query(
        "SELECT DISTINCT ctpvNm, sggNm FROM benefits "
        "WHERE scope='local' AND ctpvNm<>'' AND sggNm<>'' ORDER BY ctpvNm, sggNm"
    )
    sgg_map: dict[str, list[str]] = {}
    for r in sgg_rows:
        sgg_map.setdefault(r["ctpvNm"], []).append(r["sggNm"])
    return {
        "themes": INTEREST_THEMES,
        "households": HOUSEHOLD_SITUATIONS,
        "ctpvs": [r["ctpvNm"] for r in ctpv_rows],
        "sggMap": sgg_map,
    }


def _serialize(rows) -> list[dict]:
    return [
        {
            "servId": r["servId"],
            "servNm": r["servNm"],
            "scope": r["scope"],
            "jur": r["jur"],
            "servDgst": r["servDgst"],
            "servDtlLink": r["servDtlLink"],
            "region": (f"{r['ctpvNm']} {r['sggNm']}".strip()) if r["scope"] == "local" else "",
            "life": r["lifeArray"],
            "thema": r["themaArray"],
            "trgter": r["trgterArray"],
            "online": r["onapPsbltYn"] == "Y",
        }
        for r in rows
    ]


def _multi_condition(column: str, values: list[str]) -> tuple[str, list[str]]:
    """빈 값(제한 없음)은 통과시키고, 선택값 중 하나라도 매칭되면 통과시킨다."""
    likes = " OR ".join(f"{column} LIKE ?" for _ in values)
    params = [f"%{v}%" for v in values]
    return f"({column}='' OR {likes})", params


@app.get("/api/search")
async def search(
    age: int | None = Query(None, ge=0, le=130),
    ctpv: str | None = None,
    sgg: str | None = None,
    themes: str | None = None,   # 콤마 구분
    households: str | None = None,  # 콤마 구분
    keyword: str | None = None,
):
    await _ensure_db()

    conds: list[str] = []
    params: list = []

    if age is not None:
        stage = life_stage_from_age(age)
        conds.append("(lifeArray='' OR lifeArray LIKE ?)")
        params.append(f"%{stage}%")

    theme_list = [t for t in (themes or "").split(",") if t.strip()]
    if theme_list:
        cond, p = _multi_condition("themaArray", theme_list)
        conds.append(cond)
        params += p

    house_list = [h for h in (households or "").split(",") if h.strip()]
    if house_list:
        cond, p = _multi_condition("trgterArray", house_list)
        conds.append(cond)
        params += p

    if keyword and keyword.strip():
        conds.append("(servNm LIKE ? OR servDgst LIKE ?)")
        like = f"%{keyword.strip()}%"
        params += [like, like]

    where = (" AND " + " AND ".join(conds)) if conds else ""

    national = _query(
        f"SELECT * FROM benefits WHERE scope='national'{where} "
        f"ORDER BY servNm LIMIT {RESULT_LIMIT}",
        tuple(params),
    )

    local_rows = []
    if ctpv and ctpv.strip():
        region_cond = "scope='local' AND ctpvNm=?"
        region_params = [ctpv.strip()]
        if sgg and sgg.strip():
            # 선택한 시/군/구 + 시/도 단위(sggNm 비어있음) 사업 모두 포함
            region_cond += " AND (sggNm=? OR sggNm='')"
            region_params.append(sgg.strip())
        local_rows = _query(
            f"SELECT * FROM benefits WHERE {region_cond}{where} "
            f"ORDER BY ctpvNm, sggNm, servNm LIMIT {RESULT_LIMIT}",
            tuple(region_params + params),
        )

    return {
        "national": _serialize(national),
        "local": _serialize(local_rows),
        "limit": RESULT_LIMIT,
    }


@app.get("/api/detail/{serv_id}")
async def detail(serv_id: str):
    await _ensure_db()
    rows = _query("SELECT scope FROM benefits WHERE servId=?", (serv_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="해당 복지 서비스를 찾을 수 없습니다.")
    scope = rows[0]["scope"]
    try:
        if scope == "national":
            return await asyncio.to_thread(w.fetch_national_detail, serv_id)
        return await asyncio.to_thread(w.fetch_local_detail, serv_id)
    except w.WelfareApiError as e:
        raise HTTPException(status_code=502, detail=f"상세 조회 오류: {e}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=504, detail=f"상세 조회 실패(네트워크): {e}")


static_dir = BASE_DIR / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
