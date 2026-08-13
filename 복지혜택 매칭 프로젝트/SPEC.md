# 복지 혜택 매칭 CLI — 스펙 (v1, 2026-08-03 실제 API 호출로 확정)

## 확정 사항 (실제 호출로 검증됨)
- 중앙부처복지서비스(NationalWelfareInformationsV001): 검증 완료. List `NationalWelfarelistV001`, Detail `NationalWelfaredetailedV001`.
  실제로는 `srchKeyCode`+`searchWrd`가 사실상 필수(문서엔 애매하게 표기) — 빈 검색어(" ")를 넣으면 전체 브라우징 가능하고 그 위에 `lifeArray`/`trgterIndvdlArray`/`intrsThemaArray`/`age` 필터가 얹힘.
- 지자체복지서비스(LocalGovernmentWelfareInformations): 스키마는 마이페이지 "미리보기"로 확보(List `LcgvWelfarelist`, Detail `LcgvWelfaredetailed`). 지역은 코드가 아니라 `ctpvNm`(예: 서울특별시)/`sggNm`(예: 종로구) 이름 문자열 — **전국 어디든 free-text로 지원되므로 서울시·종로구로 범위를 제한할 이유가 없어짐** (기존 "1차: 서울시+종로구" 제한은 폐기).
  - **[2026-08-05 실호출 진단] 지자체 API는 파라미터·엔드포인트·인증키가 모두 정상인데도 모든 요청에 resultCode 10(INVALID_REQUEST_PARAMETER_ERROR)을 반환.** 진단으로 확정: (1) 없는 오퍼레이션명은 게이트웨이가 HTTP 400 NO_OPENAPI_SERVICE_ERROR를 주는데 `LcgvWelfarelist`는 HTTP 200 + `<wantedList>` 안의 rc=10을 줌 → 엔드포인트는 정확하고 백엔드까지 라우팅됨. (2) **동일 키·동일 파라미터 세트를 중앙부처 API에 보내면 rc=0 SUCCESS(461건)** → 키·필수파라미터·요청형식 문제 아님. (3) 서비스키 인코딩/디코딩 둘 다 rc=10. → 결론: **data.go.kr 게이트웨이가 아니라 사회보장정보원 원장(백엔드) 서버에 이 계정 활용신청 승인이 미반영된 것**이 원인(코드 버그 아님). 조치: `문의메일.txt`(opendata_help@nia.or.kr) 발송.
  - **[2026-08-12 해결 확인] 지자체 API 정상화됨.** 재호출 결과 rc=10 없이 정상 데이터 반환. `main.py`의 rc=10 특수 안내 메시지는 제거하고 일반 오류 처리로 단순화.
  - **[2026-08-12 추가 실측] 지자체 API는 중앙부처와 요청/응답 스키마가 다름:**
    - `age` 파라미터를 보내면 값과 무관하게 무조건 0건(rc=0, totalCount=0) 반환 — 지원하지 않는 파라미터로 추정. `fetch_local_list`에서 `age`를 아예 받지 않도록 제거하고, 생애주기 필터링은 중앙부처와 동일하게 클라이언트 사이드(`matches_life_stage`)에만 의존하도록 수정.
    - 응답 필드명이 중앙부처와 다름: 소관부처 `jurMnofNm`/`jurOrgNm` → 지자체는 `bizChrDeptNm` 하나로 옴. 생애주기/관심주제/가구상황도 코드 배열이 아니라 이미 한글 이름이 콤마로 나열된 `lifeNmArray`/`intrsThemaNmArray`/`trgterIndvdlNmArray`로 옴(요청 파라미터는 여전히 코드 기반 `lifeArray`/`intrsThemaArray`/`trgterIndvdlArray`). 상세조회도 `wlfareInfoOutlCn`→`servDgst`, `tgtrDtlCn`→`sprtTrgtCn`로 다름. `welfare_api.py`의 `_parse_serv_list`/`fetch_local_detail`에서 두 스키마를 모두 처리하도록 수정 완료.
    - `resultCode 40`(NO DATA FOUND)은 에러가 아니라 정상적인 "결과 0건" 응답인데 기존 코드가 예외로 처리하고 있었음 — `_check_result`에서 rc=40을 정상 처리(빈 리스트)로 수정.
- 성별/직업(학생·무직·직장인 등) 입력 항목은 실제 API 파라미터에 대응하는 필드가 없어 v1에서 제외. 대신 나이→생애주기 코드 자동 매핑, 관심주제(16종)·가구상황(6종) 다중선택으로 대체.
- 코드는 `codes.py`, API 클라이언트는 `welfare_api.py`, CLI는 `main.py`.

## 목적
사용자가 자신의 인적 속성(나이, 성별, 지역, 직업/가구 상황 등)을 입력하면,
공공데이터포털의 복지서비스 API를 조회해 지원 가능한 복지 혜택을 찾아
"전국 공통(중앙부처) / 시·도 단위 / 시·군·구 단위"로 구분해 보여준다.

## 데이터 소스
- 공공데이터포털(data.go.kr) Open API — 한국사회보장정보원 제공
  - 중앙부처복지서비스: https://www.data.go.kr/data/15090532/openapi.do
  - 지자체복지서비스: https://www.data.go.kr/data/15108347/openapi.do
  - 서비스 URL(확인됨): `http://apis.data.go.kr/B554287/NationalWelfareInformations`
  - 인증키는 `.env`의 `WELFARE_API_KEY`에 저장, 코드에 하드코딩 금지, git 추적 제외
- **[확인 필요]** 정확한 요청 파라미터(지역코드, 생애주기 코드, 가구상황 코드 등)와
  응답 스키마는 공공데이터포털 점검 종료 후 실제 키로 호출해 확정한다.
  조특법 프로젝트와 달리, 서버 측에서 이미 카테고리 필터링을 지원할 가능성이 높으므로
  법 조문처럼 직접 파싱하기보다는 사용자 입력값을 API 파라미터로 매핑하는 구조가 될 것으로 예상.

## 적용 범위
- 중앙부처 복지서비스 (전국 공통)
- 지자체 복지서비스 (1차: 서울특별시 + 종로구 — 사용자 거주지 기준. 다른 지역은 추후 확장)

## 입력 항목 (질문 흐름, 잠정)
1. 거주지: 시/도 (예: 서울특별시) → 시/군/구 (예: 종로구) → 읍/면/동 (예: 가회동, 참고용/추후 세분화 대비 보관)
2. 나이
3. 성별
4. 직업/가구 상황: 학생 / 무직(구직중) / 직장인 / 자영업자 / 기타 (복수 선택 가능하도록 검토)
5. 특수 조건(해당 시 선택): 저소득/기초생활수급, 한부모·조손가정, 다문화·탈북민, 장애인,
   신혼부부, 임신·출산, 다자녀, 보훈대상자 등
   — **[확인 필요]** 정확한 항목명은 API의 가구상황 코드값에 맞춰 조정

## 매칭 로직
- 사용자 입력값을 API 파라미터(지역코드, 생애주기, 가구상황 등)로 변환해 목록조회 API 호출
- 응답 결과를 중앙부처/서울시/종로구 출처별로 그룹핑해 정렬 출력
- 상세조회 API로 지원대상·선정기준·신청방법·신청기한 등 보강 조회 (조특법의 "확인 필요" 라벨과
  달리, 이번엔 API가 이미 조건별 필터링을 해주므로 기본적으로 "적용 가능"에 가깝게 표시하되,
  API가 제공하는 선정기준 텍스트도 함께 보여줘 사용자가 직접 확인할 수 있게 함)

## 출력
콘솔에 그룹별(전국 공통 / 서울시 / 종로구) 리스트로 출력. 각 항목에:
- 서비스명
- 소관 부처/지자체
- 지원 내용 요약
- 지원대상/선정기준 (API 원문)
- 신청방법·신청기한 (있는 경우)
- 상세 링크(복지로 등, API가 제공하는 경우)

## 비범위 / 주의사항
- 법적 효력 있는 복지 상담이 아님 — 최종 신청 가능 여부는 관할 주민센터/복지로 확인 필요 (면책 문구 표시)
- 서울특별시·종로구 외 지자체는 1차 버전 범위 밖 (동일 구조로 추후 확장 가능)
- API 응답 캐싱 여부는 갱신 주기 확인 후 결정 (조특법처럼 조문이 오래 유지되는 게 아니라
  복지 정책은 변동이 잦을 수 있어 캐싱보다 매 실행 시 실시간 조회가 나을 수 있음 — 확인 필요)

## 기술 스택
- Python, CLI (input() 기반 순차 질문 흐름) — 조특법 프로젝트와 동일 패턴
- requests + python-dotenv로 공공데이터포털 API 호출
- (캐싱이 필요하다고 판단되면 sqlite 추가 검토)

## 다음 단계 (점검 종료 후)
1. 공공데이터포털 점검 종료 확인, API 키 수령
2. 실제 API 호출로 요청 파라미터·응답 스키마 확정 (지역코드 목록, 생애주기/가구상황 코드 등)
3. 이 스펙의 "[확인 필요]" 항목들을 실제 값으로 채워 v1 확정
4. CLI 구현 및 테스트 (서울시 종로구, 26세 남성 프로필로 1차 검증)

## 웹앱 버전 (v2, 2026-08-12) — Render 배포

CLI를 웹으로 확장. DART 재무비율 웹앱(프로젝트111)과 동일한 배포 패턴 사용.

- **위치**: `webapp/` (FastAPI + 정적 프론트).
- **아키텍처**: 매 요청마다 공공데이터포털 API를 호출하지 않고, `build_db.py`가 중앙부처
  461 + 지자체 4,286 = **4,747건 전체를 SQLite(`data/welfare.db`)로 1회 적재**해두고
  웹앱은 로컬 DB만 조회한다. API가 느리고 간헐적 타임아웃이 있어 실시간 프록시는 무료
  플랜에서 불안정하기 때문. DB가 없으면 서버 첫 요청 때 `build_db.py`를 서브프로세스로
  자동 실행(~2분, 최초 1회). `welfare.db`는 gitignore.
- **상세조회만 실시간**: 목록/필터는 DB로 즉답, 지원대상/선정기준/급여내용 등 상세는 항목
  클릭 시 API 실시간 호출(+타임아웃 재시도 3회). 목록엔 servDgst 요약이 이미 있어 대부분
  DB만으로 충분.
- **필터링(SQL)**: 나이→생애주기 이름 매핑 후 `lifeArray LIKE`, 관심주제/가구상황 다중선택은
  `themaArray/trgterArray LIKE`(빈 값=제한없음이라 통과시켜 범용 혜택을 누락하지 않음),
  키워드는 `servNm/servDgst LIKE`. 지역: 중앙부처는 항상 포함, 지자체는 선택한 시/도(+시/군/구,
  시/도 단위 사업 포함)만.
- **엔드포인트**: `/api/options`(주제·가구·지역 선택지), `/api/search`(필터 조회, national/local
  그룹), `/api/detail/{servId}`(scope는 DB로 판별해 national/local 상세 API 호출).
- **DB 스키마 통일**: 두 API의 서로 다른 필드명을 `welfare_api._parse_serv_list`에서 흡수해
  `benefits(servId PK, servNm, scope, jur, servDgst, servDtlLink, ctpvNm, sggNm, lifeArray,
  themaArray, trgterArray, onapPsbltYn, sprtCycNm, srvPvsnNm)` 하나로 저장.
- **배포**: `render.yaml`(무료 플랜, `WELFARE_API_KEY` 환경변수), 상세 절차는 `webapp/DEPLOY.md`.
- **스택**: fastapi, uvicorn[standard], requests, python-dotenv (pandas/무거운 의존성 없음 → 경량).
