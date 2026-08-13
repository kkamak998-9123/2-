# -*- coding: utf-8 -*-
"""공공데이터포털(한국사회보장정보원, B554287) 복지서비스 Open API 클라이언트.

- 중앙부처복지서비스(NationalWelfareInformationsV001)
- 지자체복지서비스(LocalGovernmentWelfareInformations)

CLI 버전과 달리 웹앱에서는 (1) 전체 목록을 SQLite로 적재하기 위한 페이지네이션
헬퍼(`iter_national_all`/`iter_local_all`)와 (2) 상세 실시간 조회 시 일시적
타임아웃에 대비한 재시도를 추가로 제공한다.

두 API의 응답 스키마가 서로 다르다(실측 2026-08-12):
- 소관부처: 중앙부처 jurMnofNm/jurOrgNm  vs  지자체 bizChrDeptNm
- 생애/주제/가구 배열: 중앙부처 lifeArray/intrsThemaArray/trgterIndvdlArray
  vs  지자체 lifeNmArray/intrsThemaNmArray/trgterIndvdlNmArray
  (둘 다 값은 코드가 아니라 한글 이름 CSV: 예 "영유아,아동,청소년")
- 상세 요약/지원대상: 중앙부처 wlfareInfoOutlCn/tgtrDtlCn  vs  지자체 servDgst/sprtTrgtCn
- 지자체 목록은 age 파라미터를 주면 값과 무관하게 0건을 반환하므로 보내지 않는다.
"""

import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

# 로컬 개발 시 프로젝트 루트(webapp의 상위)의 .env를 읽는다.
# Render 등 배포 환경에는 .env가 없고 환경변수(WELFARE_API_KEY)로 주입된다.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()  # webapp/.env 또는 CWD의 .env도 있으면 보조로 로드

_RAW_KEY = os.environ.get("WELFARE_API_KEY", "")
SERVICE_KEY = urllib.parse.unquote(_RAW_KEY) if _RAW_KEY else ""

NATIONAL_BASE = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"
LOCAL_BASE = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"

TIMEOUT = 20
RETRIES = 3
NO_DATA_CODE = "40"  # NO DATA FOUND — 오류가 아니라 정상적인 "결과 0건" 응답


class WelfareApiError(Exception):
    def __init__(self, result_code, result_message):
        self.result_code = result_code
        self.result_message = result_message
        super().__init__(f"[{result_code}] {result_message}")


def _get(url, params):
    params = {"serviceKey": SERVICE_KEY, **params}
    last_err = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return ET.fromstring(resp.content)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise last_err


def _text(el, tag, default=""):
    child = el.find(tag)
    return child.text if child is not None and child.text else default


def _check_result(root):
    result_code = _text(root, "resultCode", None)
    result_message = _text(root, "resultMessage", "")
    if result_code in ("0", None, NO_DATA_CODE):
        return
    raise WelfareApiError(result_code, result_message)


def _total_count(root):
    tc = root.find("totalCount")
    try:
        return int(tc.text) if tc is not None and tc.text else 0
    except ValueError:
        return 0


def _parse_serv_list(root):
    """중앙부처/지자체 목록 스키마 차이를 흡수해 통일된 dict로 변환한다."""
    services = []
    for serv in root.findall(".//servList"):
        jur = (_text(serv, "jurMnofNm") + " " + _text(serv, "jurOrgNm")).strip()
        if not jur:
            jur = _text(serv, "bizChrDeptNm")
        services.append(
            {
                "servId": _text(serv, "servId"),
                "servNm": _text(serv, "servNm"),
                "jur": jur,
                "servDgst": _text(serv, "servDgst"),
                "servDtlLink": _text(serv, "servDtlLink"),
                "ctpvNm": _text(serv, "ctpvNm"),
                "sggNm": _text(serv, "sggNm"),
                "lifeArray": _text(serv, "lifeArray") or _text(serv, "lifeNmArray"),
                "trgterArray": _text(serv, "trgterIndvdlArray")
                or _text(serv, "trgterIndvdlNmArray"),
                "themaArray": _text(serv, "intrsThemaArray")
                or _text(serv, "intrsThemaNmArray"),
                "sprtCycNm": _text(serv, "sprtCycNm"),
                "srvPvsnNm": _text(serv, "srvPvsnNm"),
                "onapPsbltYn": _text(serv, "onapPsbltYn"),
            }
        )
    return services


# ---------------------------------------------------------------------------
# 전체 적재용 페이지네이션 헬퍼 (build_db.py에서 사용)
# ---------------------------------------------------------------------------

def iter_national_all(num_of_rows=100):
    """중앙부처 전체 복지서비스를 페이지 단위로 모두 내려받아 yield한다."""
    page = 1
    total = None
    seen = 0
    while True:
        root = _get(
            f"{NATIONAL_BASE}/NationalWelfarelistV001",
            {
                "callTp": "L",
                "pageNo": page,
                "numOfRows": num_of_rows,
                "srchKeyCode": "003",
                "searchWrd": " ",
            },
        )
        _check_result(root)
        if total is None:
            total = _total_count(root)
        items = _parse_serv_list(root)
        if not items:
            break
        for it in items:
            it["scope"] = "national"
            it["ctpvNm"] = ""
            it["sggNm"] = ""
            yield it
        seen += len(items)
        if total and seen >= total:
            break
        page += 1


def iter_local_all(num_of_rows=100):
    """지자체 전체 복지서비스를 페이지 단위로 모두 내려받아 yield한다."""
    page = 1
    total = None
    seen = 0
    while True:
        root = _get(
            f"{LOCAL_BASE}/LcgvWelfarelist",
            {
                "pageNo": page,
                "numOfRows": num_of_rows,
                "srchKeyCode": "003",
                "searchWrd": " ",
                "arrgOrd": "001",
            },
        )
        _check_result(root)
        if total is None:
            total = _total_count(root)
        items = _parse_serv_list(root)
        if not items:
            break
        for it in items:
            it["scope"] = "local"
            yield it
        seen += len(items)
        if total and seen >= total:
            break
        page += 1


# ---------------------------------------------------------------------------
# 상세 실시간 조회 (웹앱에서 항목 클릭 시)
# ---------------------------------------------------------------------------

def fetch_national_detail(serv_id):
    root = _get(
        f"{NATIONAL_BASE}/NationalWelfaredetailedV001",
        {"callTp": "D", "servId": serv_id},
    )
    _check_result(root)
    return {
        "servId": _text(root, "servId"),
        "servNm": _text(root, "servNm"),
        "jur": _text(root, "jurMnofNm"),
        "outline": _text(root, "wlfareInfoOutlCn"),
        "target": _text(root, "tgtrDtlCn"),
        "criteria": _text(root, "slctCritCn"),
        "benefit": _text(root, "alwServCn"),
        "cycle": _text(root, "sprtCycNm"),
        "provision": _text(root, "srvPvsnNm"),
        "applyMethod": [
            _text(item, "servSeDetailLink") or _text(item, "servSeDetailNm")
            for item in root.findall("applmetList")
        ],
    }


def fetch_local_detail(serv_id):
    root = _get(f"{LOCAL_BASE}/LcgvWelfaredetailed", {"servId": serv_id})
    _check_result(root)
    apply_method = _text(root, "aplyMtdCn") or _text(root, "aplyMtdNm")
    return {
        "servId": _text(root, "servId"),
        "servNm": _text(root, "servNm"),
        "jur": _text(root, "bizChrDeptNm"),
        "outline": _text(root, "servDgst"),
        "target": _text(root, "sprtTrgtCn"),
        "criteria": _text(root, "slctCritCn"),
        "benefit": _text(root, "alwServCn"),
        "cycle": _text(root, "sprtCycNm"),
        "provision": _text(root, "srvPvsnNm"),
        "applyMethod": [apply_method] if apply_method else [],
    }
