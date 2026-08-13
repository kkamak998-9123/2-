# 배포 가이드 — 복지혜택 매칭 웹앱 (Render + SQLite)

DART 재무비율 웹앱(프로젝트111)과 동일한 구조로 배포한다.

## 구성 요약
- **웹서버**: FastAPI (`main.py`) — `uvicorn main:app`
- **DB**: SQLite `data/welfare.db` (`build_db.py`가 공공데이터포털 API로 전체 4,700여 건을 1회 적재)
  - `welfare.db`는 gitignore 됨. 서버가 처음 뜰 때 DB가 없으면 `build_db.py`를 자동 실행해 만든다(최초 1회 ~2분).
- **상세조회**: 항목 클릭 시에만 공공데이터포털 API를 실시간 호출(DB엔 목록만 저장).
- **환경변수**: `WELFARE_API_KEY` (공공데이터포털 인증키). Render에 반드시 등록.

## 방법 A) 전용 저장소 + Render (프로젝트111과 동일, 권장)

1. GitHub에서 새 저장소 생성: 예 `welfare-benefit-matcher` (public/private 무관).
2. 이 `webapp/` 폴더의 **내용물을 저장소 루트**에 올린다:
   ```bash
   cd "복지혜택 매칭 프로젝트/webapp"
   git init
   git add .              # welfare.db는 .gitignore로 자동 제외됨
   git commit -m "복지혜택 매칭 웹앱 초기 배포본"
   git branch -M main
   git remote add origin https://github.com/<사용자>/welfare-benefit-matcher.git
   git push -u origin main
   ```
3. Render 대시보드 → **New → Web Service** → 위 저장소 연결.
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
   - **Environment → Add Environment Variable**: `WELFARE_API_KEY` = (공공데이터포털 인증키, 디코딩 키)
   - (저장소에 `render.yaml`이 있으므로 Blueprint로 생성해도 됨)
4. 첫 배포 후 첫 접속 시 DB 적재로 1~2분 걸린다. 이후엔 즉시 응답.

## 방법 B) 모노레포 서브디렉터리로 배포
Render Web Service의 **Root Directory**를 `복지혜택 매칭 프로젝트/webapp`으로 지정하고
모노레포(`2-`)를 연결. push 시 자동 배포되나, 한글/공백 경로 이슈 가능성이 있어 방법 A를 권장.

## 로컬 실행/테스트
```bash
cd "복지혜택 매칭 프로젝트/webapp"
python build_db.py          # (선택) DB 미리 생성. 안 하면 첫 요청 때 자동 생성
uvicorn main:app --reload --port 8000
# http://127.0.0.1:8000
```
`.env`(프로젝트 루트)에 `WELFARE_API_KEY=...` 필요.

## 데이터 갱신
복지 정책은 변동되므로 주기적으로 DB를 새로 만들면 된다:
- 로컬: `python build_db.py` 후 재배포, 또는
- Render: `data/welfare.db`를 지우고 재시작하면 다음 요청 때 자동 재적재.
