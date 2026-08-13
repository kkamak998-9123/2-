# -*- coding: utf-8 -*-
"""실손보험 세대별 청구액 계산 웹앱 (FastAPI).

영수증 금액(급여 본인부담·비급여·특약 비급여)을 입력받아 1~4세대(2세대는
2-1/2-2 분리) 표준 규칙으로 예상 수령액을 계산해 비교한다. 외부 API/DB
불필요 — 순수 계산이므로 계산 로직은 calc.py/rules.py에 격리해 테스트한다.
"""

from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from calc import RIDER_NAMES, calculate_all
from rules import HOSPITAL_TYPES

BASE_DIR = Path(__file__).parent

app = FastAPI(title="실손보험 세대별 청구액 계산기")
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


class CalcRequest(BaseModel):
    care_type: Literal["입원", "통원", "처방조제"]
    hospital_type: Literal["의원", "병원", "상급종합"] = "의원"
    paid_copay: float = Field(0, ge=0, le=100_000_000)
    nonpaid: float = Field(0, ge=0, le=100_000_000)
    rider_dosu: float = Field(0, ge=0, le=100_000_000)   # 도수·체외충격파·증식치료
    rider_injection: float = Field(0, ge=0, le=100_000_000)  # 비급여 주사
    rider_mri: float = Field(0, ge=0, le=100_000_000)  # 비급여 MRI/MRA


@app.get("/api/meta")
async def get_meta():
    return {
        "careTypes": ["입원", "통원", "처방조제"],
        "hospitalTypes": HOSPITAL_TYPES,
        "riders": list(RIDER_NAMES),
    }


@app.post("/api/calc")
async def calc(req: CalcRequest):
    if req.paid_copay == 0 and req.nonpaid == 0 and not any(
        [req.rider_dosu, req.rider_injection, req.rider_mri]
    ):
        raise HTTPException(status_code=400, detail="금액을 하나 이상 입력해주세요.")

    riders = {
        "도수": req.rider_dosu,
        "주사": req.rider_injection,
        "MRI": req.rider_mri,
    }
    results = calculate_all(
        care_type=req.care_type,
        hospital_type=req.hospital_type,
        paid_copay=req.paid_copay,
        nonpaid=req.nonpaid,
        riders=riders,
    )
    best = max(results, key=lambda r: r["expected_payout"])
    return {"results": results, "best_generation": best["generation"]}


static_dir = BASE_DIR / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
