import os
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv()

_RAW_KEY = os.environ["WELFARE_API_KEY"]
SERVICE_KEY = urllib.parse.unquote(_RAW_KEY)

NATIONAL_BASE = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"
LOCAL_BASE = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"

TIMEOUT = 15


class WelfareApiError(Exception):
    def __init__(self, result_code, result_message):
        self.result_code = result_code
        self.result_message = result_message
        super().__init__(f"[{result_code}] {result_message}")


def _get(url, params):
    params = {"serviceKey": SERVICE_KEY, **params}
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def _text(el, tag, default=""):
    child = el.find(tag)
    return child.text if child is not None and child.text else default


NO_DATA_CODE = "40"


def _check_result(root):
    result_code = _text(root, "resultCode", None)
    result_message = _text(root, "resultMessage", "")
    if result_code in ("0", None, NO_DATA_CODE):
        return
    raise WelfareApiError(result_code, result_message)


def _parse_serv_list(root):
    # 중앙부처(jurMnofNm/jurOrgNm, lifeArray 등 코드성 필드)와 지자체
    # (bizChrDeptNm, lifeNmArray 등 이름 배열 필드) 응답 스키마가 서로 달라
    # 각 필드마다 두 스키마의 태그명을 순서대로 시도한다(실측 확인, 2026-08-12).
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
                "lifeArray": _text(serv, "lifeArray") or _text(serv, "lifeNmArray"),
                "trgterIndvdlArray": _text(serv, "trgterIndvdlArray")
                or _text(serv, "trgterIndvdlNmArray"),
                "intrsThemaArray": _text(serv, "intrsThemaArray")
                or _text(serv, "intrsThemaNmArray"),
                "sprtCycNm": _text(serv, "sprtCycNm"),
                "srvPvsnNm": _text(serv, "srvPvsnNm"),
                "onapPsbltYn": _text(serv, "onapPsbltYn"),
            }
        )
    return services


def fetch_national_list(
    life_array=None,
    trgter_indvdl_array=None,
    intrs_thema_array=None,
    age=None,
    search_wrd="",
    srch_key_code="003",
    page_no=1,
    num_of_rows=20,
):
    params = {
        "callTp": "L",
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "srchKeyCode": srch_key_code,
        "searchWrd": search_wrd or " ",
    }
    if life_array:
        params["lifeArray"] = life_array
    if trgter_indvdl_array:
        params["trgterIndvdlArray"] = trgter_indvdl_array
    if intrs_thema_array:
        params["intrsThemaArray"] = intrs_thema_array
    if age is not None:
        params["age"] = age

    root = _get(f"{NATIONAL_BASE}/NationalWelfarelistV001", params)
    _check_result(root)
    return _parse_serv_list(root)


def fetch_national_detail(serv_id):
    root = _get(
        f"{NATIONAL_BASE}/NationalWelfaredetailedV001",
        {"callTp": "D", "servId": serv_id},
    )
    _check_result(root)
    detail = root
    return {
        "servId": _text(detail, "servId"),
        "servNm": _text(detail, "servNm"),
        "jurMnofNm": _text(detail, "jurMnofNm"),
        "wlfareInfoOutlCn": _text(detail, "wlfareInfoOutlCn"),
        "tgtrDtlCn": _text(detail, "tgtrDtlCn"),
        "slctCritCn": _text(detail, "slctCritCn"),
        "alwServCn": _text(detail, "alwServCn"),
        "sprtCycNm": _text(detail, "sprtCycNm"),
        "srvPvsnNm": _text(detail, "srvPvsnNm"),
        "applmet": [
            _text(item, "servSeDetailLink") or _text(item, "servSeDetailNm")
            for item in detail.findall("applmetList")
        ],
    }


def fetch_local_list(
    ctpv_nm=None,
    sgg_nm=None,
    life_array=None,
    trgter_indvdl_array=None,
    intrs_thema_array=None,
    search_wrd="",
    srch_key_code="003",
    arrg_ord="001",
    page_no=1,
    num_of_rows=20,
):
    # 지자체 API는 age 파라미터가 있으면 값과 무관하게 무조건 0건을 반환한다
    # (실측 확인, 2026-08-12) — 의도적으로 지원하지 않으므로 여기서 받지 않는다.
    params = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "srchKeyCode": srch_key_code,
        "searchWrd": search_wrd or " ",
        "arrgOrd": arrg_ord,
    }
    if ctpv_nm:
        params["ctpvNm"] = ctpv_nm
    if sgg_nm:
        params["sggNm"] = sgg_nm
    if life_array:
        params["lifeArray"] = life_array
    if trgter_indvdl_array:
        params["trgterIndvdlArray"] = trgter_indvdl_array
    if intrs_thema_array:
        params["intrsThemaArray"] = intrs_thema_array

    root = _get(f"{LOCAL_BASE}/LcgvWelfarelist", params)
    _check_result(root)
    return _parse_serv_list(root)


def fetch_local_detail(serv_id):
    # 지자체 상세 스키마는 중앙부처와 태그명이 다르다(실측 확인, 2026-08-12):
    # jurMnofNm -> bizChrDeptNm, wlfareInfoOutlCn -> servDgst, tgtrDtlCn -> sprtTrgtCn.
    root = _get(f"{LOCAL_BASE}/LcgvWelfaredetailed", {"servId": serv_id})
    _check_result(root)
    detail = root
    return {
        "servId": _text(detail, "servId"),
        "servNm": _text(detail, "servNm"),
        "jur": _text(detail, "bizChrDeptNm"),
        "wlfareInfoOutlCn": _text(detail, "servDgst"),
        "tgtrDtlCn": _text(detail, "sprtTrgtCn"),
        "slctCritCn": _text(detail, "slctCritCn"),
        "alwServCn": _text(detail, "alwServCn"),
        "sprtCycNm": _text(detail, "sprtCycNm"),
        "srvPvsnNm": _text(detail, "srvPvsnNm"),
    }
