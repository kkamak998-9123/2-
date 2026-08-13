"""사용자 프로필과 조특법 특례 조항을 매칭한다."""
from provisions import PROVISIONS, STATUS_OK, STATUS_CHECK, STATUS_NO
from corp_provisions import CORP_PROVISIONS

_STATUS_ORDER = {STATUS_OK: 0, STATUS_CHECK: 1, STATUS_NO: 2}

ALL_PROVISIONS = PROVISIONS + CORP_PROVISIONS


def _display_no(article: str, branch: str) -> str:
    return f"제{article}조" + (f"의{branch}" if branch else "")


def match(profile: dict) -> list[dict]:
    results = []
    for p in ALL_PROVISIONS:
        status, rate, cap, deadline, note = p["eval"](profile)
        if status == STATUS_NO:
            continue
        results.append(
            {
                "조번호": _display_no(p["article"], p["branch"]),
                "article": p["article"],
                "branch": p["branch"],
                "특례명": p["title"],
                "상태": status,
                "감면율": rate,
                "한도금액": cap,
                "적용기한": deadline,
                "확인사항": note,
            }
        )
    results.sort(key=lambda r: _STATUS_ORDER[r["상태"]])
    return results
