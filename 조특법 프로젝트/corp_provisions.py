"""조세특례제한법 법인(및 사업소득) 특례 — v2 확장분.

law.go.kr 원문(MST 280409, 2026-07-01 시행)을 근거로 요약. 20개 후보 조항을
검토한 결과 26조(고용창출투자세액공제, 2017년 투자분까지), 29조의5(청년고용증대,
2017년 과세연도까지), 29조의7(고용증대, 2024년 과세연도까지), 30조의4(사회보험료,
2024년/2020년까지)는 적용기한이 이미 지나 사실상 만료된 조항이라 제외했다.
"""
from provisions import STATUS_OK, STATUS_CHECK, STATUS_NO


def _eligible_entity(pf):
    return pf.get("is_corp") or pf.get("is_business_owner")


def _p12_2(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "연구개발특구":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "최초 3년 100% + 다음 2년 50%",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/연구인력/서비스업은 2,000만원)",
        "2028-12-31까지 지정·등록분",
        "연구개발특구 첨단기술기업·연구소기업 지정/등록 요건 충족 여부 확인 필요.",
    )


def _p24(pf):
    if not _eligible_entity(pf):
        return STATUS_NO, None, None, None, None
    size = pf.get("company_size")
    if size == "중소기업":
        rate = "일반자산 10%, 신성장사업화시설 12~18%, 국가전략기술시설 15~25%(반도체 20~30%)"
    elif size == "중견기업":
        rate = "일반자산 5~7%, 신성장사업화시설 8~10%, 국가전략기술시설 15~25%"
    else:
        rate = "일반자산 1~3%, 신성장사업화시설 3~6%, 국가전략기술시설 15~25%"
    return (
        STATUS_CHECK,
        rate + " (자산 유형·연도별로 세분화, 추가공제 별도)",
        "추가공제: 직전 3년 평균 초과 투자분의 10% (기본공제 2배 한도)",
        "국가전략기술시설은 2029-12-31까지 투자분, 일반자산은 매년 개정",
        "통합투자세액공제. 사업용 유형자산 투자 시 적용. 정확한 공제율은 자산 종류·투자연도별로 시행령 확인 필요.",
    )


def _p29_4(pf):
    if not _eligible_entity(pf):
        return STATUS_NO, None, None, None, None
    size = pf.get("company_size")
    if size == "대기업":
        return STATUS_NO, None, None, None, None  # 중소·중견기업만 대상
    if size is None:
        return STATUS_CHECK, None, None, None, "대기업은 대상이 아니므로, 기업 규모(중소/중견)를 먼저 확인해야 함."
    if pf.get("wage_increased") is not True:
        return STATUS_CHECK, None, None, None, "상시근로자 평균임금 증가율이 직전 3년 평균보다 커야 적용됨. 해당 여부 미확인."
    rate = "100분의 10 (중견기업)" if size == "중견기업" else "100분의 20 (중소기업)"
    return (
        STATUS_OK,
        rate,
        "직전 3년 평균 초과 임금증가분 기준 산정 (한도 규정 없음)",
        "2028-12-31이 속하는 과세연도까지",
        "정규직 전환자 특례(3항)는 임금증가분과 별도 요건으로 추가 공제 가능.",
    )


def _p29_8(pf):
    if not _eligible_entity(pf):
        return STATUS_NO, None, None, None, None
    if pf.get("employment_increased") is not True:
        return STATUS_CHECK, None, None, None, "상시근로자 수가 직전 3개 과세연도 중 1개 이상보다 증가해야 적용됨. 해당 여부 미확인."
    size = pf.get("company_size")
    if size == "중소기업":
        rate = "청년등 상시근로자 1인당 700만~2,000만원 + 청년등 외 1인당 400만~1,000만원 (수도권외 가산)"
    elif size == "중견기업":
        rate = "청년등 상시근로자 1인당 500만~900만원 + 청년등 외 1인당 300만~500만원"
    else:
        rate = "청년등상시근로자 증가분만 300만~500만원 (청년등 외 증가는 최소고용증가인원 초과분만 일부 인정)"
    return (
        STATUS_CHECK,
        rate + " (직전/전전/전전전 과세연도 대비 증가분을 3년간 나눠 공제)",
        "청년등상시근로자·청년등외상시근로자 증가 인원수 기준 산정 (한도 규정 없음)",
        "2026~2028-12-31이 속하는 과세연도 (육아휴직 복귀자 조항은 2026-12-31까지 복직분)",
        "통합고용세액공제. 3년 뒤 인원이 감소하면 공제세액 추징됨에 유의.",
    )


def _relocation_common(pf, kind):
    if not _eligible_entity(pf):
        return STATUS_NO, None, None, None, None
    if pf.get("relocation_type") not in ("공장", "본사", "둘다"):
        return STATUS_NO, None, None, None, None
    if kind == "공장" and pf["relocation_type"] not in ("공장", "둘다"):
        return STATUS_NO, None, None, None, None
    if kind == "본사" and pf["relocation_type"] not in ("본사", "둘다"):
        return STATUS_NO, None, None, None, None
    return None


def _p60(pf):
    if not pf.get("is_corp"):
        return STATUS_NO, None, None, None, None
    skip = _relocation_common(pf, "공장")
    if skip:
        return skip
    if pf.get("region") not in ("seoul_dense",):
        return STATUS_CHECK, None, None, None, "수도권과밀억제권역(또는 그에 준하는 대통령령 지정지역)에서 지방으로 이전하는 경우만 해당."
    return (
        STATUS_CHECK,
        "양도차익 익금불산입 (5년 거치 후 5년간 균분 익금산입)",
        "이월결손금 차감 후 잔액 범위",
        "2028-12-31까지 양도분",
        "대도시(수도권과밀억제권역 등)에서 지방으로 공장을 이전하며 대지·건물을 양도하는 경우. 이전 전후 업종 동일 요건.",
    )


def _p61(pf):
    if not pf.get("is_corp"):
        return STATUS_NO, None, None, None, None
    skip = _relocation_common(pf, "본사")
    if skip:
        return skip
    if pf.get("region") != "seoul_dense":
        return STATUS_CHECK, None, None, None, "수도권과밀억제권역에 본점·주사무소가 있던 법인만 해당."
    return (
        STATUS_CHECK,
        "양도차익 익금불산입 (5년 거치 후 5년간 균분 익금산입)",
        "이월결손금 차감 후 잔액 범위",
        "2028-12-31까지 양도분",
        "수도권과밀억제권역 밖으로 본사 이전 시 종전 대지·건물 양도차익 특례. 이전 후 재이전·수도권 사무소 유지 시 추징.",
    )


def _p62(pf):
    if not (pf.get("is_corp") and pf.get("is_public_agency_relocation")):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "양도차익 익금불산입 (5년 거치 후 5년간 균분 익금산입)",
        "이월결손금 차감 후 잔액 범위",
        "종전부동산 양도분 2026-12-31까지",
        "혁신도시 조성 및 발전에 관한 특별법상 '이전공공기관'만 해당 (일반 민간법인 제외). "
        "법인세 전액(2년)+50%(2년) 추가 감면(4항)은 2018-12-31 이전 이전분까지만 적용되어 현재는 만료됨 — "
        "양도차익 익금불산입 특례만 유효.",
    )


def _p63(pf):
    skip = _relocation_common(pf, "공장")
    if skip:
        return skip
    size = pf.get("company_size")
    region = pf.get("region")
    if size == "중소기업" and region in ("nonseoul", "seoul_decline"):
        rate = "100% (5~10년) 이후 50% (3~5년)"
    else:
        rate = "이전지역·성장촉진지역등 해당 여부에 따라 100%(5~10년)+50%(3~5년) 세분화"
    return (
        STATUS_CHECK,
        rate,
        "투자누계액의 70% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 사업개시 (신축 시 2031-12-31)",
        "수도권과밀억제권역에 2~3년 이상 소재했던 공장을 수도권 밖으로 완전 이전해야 함. 광역시 이전 시 산업단지 입주 등 추가요건.",
    )


def _p63_2(pf):
    if not pf.get("is_corp"):
        return STATUS_NO, None, None, None, None
    skip = _relocation_common(pf, "본사")
    if skip:
        return skip
    return (
        STATUS_CHECK,
        "이전지역·성장촉진지역등 해당 여부에 따라 100%(5~10년)+50%(3~5년)",
        "투자누계액의 70% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 사업개시 (신축 시 2031-12-31)",
        "수도권과밀억제권역에 3년 이상 있던 본사를 수도권 밖으로 이전. 부동산업·건설업·소비성서비스업 등은 제외.",
    )


def _p64(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") not in ("농공단지", "중소기업특별지원지역"):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100분의 50",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 입주분",
        "농공단지 또는 중소기업특별지원지역 입주 요건 확인 필요.",
    )


def _p99_9(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "위기지역":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100% (5년) 이후 50% (2년)",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 창업·사업장 신설 (위기지역 지정 기간 내)",
        "고용위기지역·산업위기대응특별지역 등 '위기지역' 지정 및 투자·고용 기준 충족 여부 확인 필요.",
    )


def _p121_8(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "제주첨단과학기술단지":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100% (3년) 이후 50% (2년)",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 입주분",
        "제주첨단과학기술단지 입주 및 감면대상사업(생물산업·정보통신산업 등) 여부 확인 필요.",
    )


def _p121_9(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "제주투자진흥지구":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100%(3년)+50%(2년) — 제주자유무역지역·개발사업시행자는 50%/25%",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "제주투자진흥지구 2028-12-31까지 입주 (자유무역지역은 2021-12-31 만료)",
        "제주자유무역지역 조항(제1항제2호)은 2021-12-31로 이미 만료되어 제주투자진흥지구 입주만 유효.",
    )


def _p121_17(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "기업도시등":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "100%(3년)+50%(2년) 또는 50%(3년)+25%(2년) — 구역 유형에 따라 상이",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 창업·사업장 신설",
        "기업도시개발구역·지역개발사업구역·새만금투자진흥지구·평화경제특구 등 세부 구역 유형에 따라 감면율이 다름. 정확한 구역 확인 필요.",
    )


def _p121_33(pf):
    if not _eligible_entity(pf) or pf.get("zone_type") != "기회발전특구":
        return STATUS_NO, None, None, None, None
    return (
        STATUS_OK,
        "100% (5년) 이후 50% (2년)",
        "투자누계액의 50% + 상시근로자 수×1,500만원(청년/서비스업 2,000만원)",
        "2028-12-31까지 창업·사업장 신설 (기회발전특구 지정 기간 내)",
        "기회발전특구 지정 기간 중 제조업 등 대통령령으로 정하는 업종으로 창업/신설해야 함. 기존 사업장 이전은 제외.",
    )


def _p121_34(pf):
    if not (_eligible_entity(pf) and pf.get("zone_type") == "기회발전특구" and pf.get("relocation_type")):
        return STATUS_NO, None, None, None, None
    return (
        STATUS_CHECK,
        "양도차익 상당액 익금불산입(법인) / 과세이연(개인)",
        "대통령령으로 정하는 방법에 따라 계산한 양도차익상당액",
        "종전 사업용부동산 2026-12-31까지 양도",
        "수도권에서 3년(중소기업 2년) 이상 사업 영위 후 기회발전특구로 사업용부동산 이전 시. 양도기한이 임박했으니 서두를 것.",
    )


CORP_PROVISIONS = [
    {"article": "12", "branch": "2", "title": "연구개발특구에 입주하는 첨단기술기업 등에 대한 법인세 등의 감면", "eval": _p12_2},
    {"article": "24", "branch": "", "title": "통합투자세액공제", "eval": _p24},
    {"article": "29", "branch": "4", "title": "근로소득을 증대시킨 기업에 대한 세액공제", "eval": _p29_4},
    {"article": "29", "branch": "8", "title": "통합고용세액공제", "eval": _p29_8},
    {"article": "60", "branch": "", "title": "공장의 대도시 밖 이전에 대한 법인세 과세특례", "eval": _p60},
    {"article": "61", "branch": "", "title": "법인 본사를 수도권과밀억제권역 밖으로 이전하는 데 따른 양도차익에 대한 법인세 과세특례", "eval": _p61},
    {"article": "62", "branch": "", "title": "공공기관이 혁신도시 등으로 이전하는 경우 법인세 등 감면", "eval": _p62},
    {"article": "63", "branch": "", "title": "수도권 밖으로 공장을 이전하는 기업에 대한 세액감면 등", "eval": _p63},
    {"article": "63", "branch": "2", "title": "수도권 밖으로 본사를 이전하는 법인에 대한 세액감면 등", "eval": _p63_2},
    {"article": "64", "branch": "", "title": "농공단지 입주기업 등에 대한 세액감면", "eval": _p64},
    {"article": "99", "branch": "9", "title": "위기지역 창업기업에 대한 법인세 등의 감면", "eval": _p99_9},
    {"article": "121", "branch": "8", "title": "제주첨단과학기술단지 입주기업에 대한 법인세 등의 감면", "eval": _p121_8},
    {"article": "121", "branch": "9", "title": "제주투자진흥지구 또는 제주자유무역지역 입주기업에 대한 법인세 등의 감면", "eval": _p121_9},
    {"article": "121", "branch": "17", "title": "기업도시개발구역 등의 창업기업 등에 대한 법인세 등의 감면", "eval": _p121_17},
    {"article": "121", "branch": "33", "title": "기회발전특구의 창업기업 등에 대한 법인세 등의 감면", "eval": _p121_33},
    {"article": "121", "branch": "34", "title": "기회발전특구로 이전하는 기업에 대한 과세특례", "eval": _p121_34},
]
