# -*- coding: utf-8 -*-
"""비상장주식 평가 계산기: 상증세법 시행령상 보충적 평가방법 API + 정적 프론트엔드"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from financials import FinancialsParseError, parse_all
from valuation import run_valuation, ValuationError, SPECIAL_CORP_TYPES

app = FastAPI(title="비상장주식 평가 계산기")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


class AdjustmentItem(BaseModel):
    name: str
    amount: float


class YearInput(BaseModel):
    label: str
    net_income: float
    additions: list[AdjustmentItem] = Field(default_factory=list)
    subtractions: list[AdjustmentItem] = Field(default_factory=list)


class NetAssetInput(BaseModel):
    total_assets: float
    total_liabilities: float
    goodwill: float = 0.0


class MajorShareholderInput(BaseModel):
    is_major_shareholder: bool = False
    is_exempt: bool = False
    premium_rate: float = 20.0


class ValuationRequest(BaseModel):
    shares_outstanding: float
    capitalization_rate: float = 10.0
    years: list[YearInput]
    net_asset: NetAssetInput
    special_corp_type: str = "normal"
    major_shareholder: Optional[MajorShareholderInput] = None


@app.get("/api/special-corp-types")
def list_special_corp_types():
    return [{"id": k, "label": v} for k, v in SPECIAL_CORP_TYPES.items()]


@app.post("/api/calculate")
def calculate(req: ValuationRequest):
    payload = req.model_dump()
    try:
        result = run_valuation(payload)
    except ValuationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/api/parse-financials")
async def parse_financials(
    balance_sheet: UploadFile = File(...),
    income_statements: UploadFile = File(...),
    adjustments: UploadFile = File(...),
):
    try:
        result = parse_all(
            balance_sheet_bytes=await balance_sheet.read(),
            income_bytes=await income_statements.read(),
            adjustments_bytes=await adjustments.read(),
        )
    except FinancialsParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
