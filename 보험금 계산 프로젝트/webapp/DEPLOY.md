# 배포 가이드 — 실손보험 세대별 청구액 계산기 (Render)

복지혜택 매칭 웹앱과 동일한 배포 패턴. 이 프로젝트는 **외부 API 키나 DB가 없는
순수 계산 웹앱**이라 훨씬 간단하다 — 환경변수 설정도 필요 없음.

## 구성 요약
- **웹서버**: FastAPI (`main.py`) — `uvicorn main:app`
- **계산 엔진**: `calc.py` + `rules.py` (순수 파이썬, 외부 의존성 없음)
- **환경변수**: 없음

## 배포 절차 (전용 저장소 + Render)

1. GitHub에서 새 빈 저장소 생성: 예 `insurance-claim-calculator`
   (README·gitignore 체크 없이 빈 저장소로 생성)

2. 이 `webapp/` 폴더는 이미 git 저장소로 초기화·커밋되어 있음. 아래 두 줄만 실행:
   ```bash
   cd "보험금 계산 프로젝트/webapp"
   git remote add origin https://github.com/<본인계정>/insurance-claim-calculator.git
   git push -u origin main
   ```

3. Render 대시보드 → **New → Web Service** → 위 저장소 연결.
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
   - 환경변수 설정 불필요 (저장소에 `render.yaml` 있어 Blueprint로 생성해도 자동 인식)

4. 배포 후 바로 사용 가능 (DB 적재·콜드스타트 지연 없음 — 순수 계산이라 즉시 응답).

## 로컬 실행/테스트
```bash
cd "보험금 계산 프로젝트/webapp"
uvicorn main:app --reload --port 8000
# http://127.0.0.1:8000
```

## 계산 로직 변경 시
루트의 `rules.py`/`calc.py`가 원본이고, `webapp/`의 동일 파일은 배포용 복사본이다.
규칙(세율·한도 등)을 바꿀 땐 루트에서 수정 → 테스트(`python -m unittest test_calc`)
통과 확인 → `webapp/`에 복사 → 커밋·푸시.
