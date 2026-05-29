# SSD Price Tracker

SSD 가격을 자동으로 수집하고, 가격 이력과 상품별 상태를 웹 대시보드에서 확인할 수 있는 가격 추적 프로젝트입니다.

초기에는 CSV 파일에 가격을 기록하는 로컬 스크립트로 시작했지만, 상품 관리와 가격 이력 조회가 복잡해지는 문제가 있었습니다. 이후 SQLite 저장 구조, FastAPI 대시보드, 상품 관리 UI, Turso 클라우드 DB, GitHub Actions 자동 실행까지 확장했습니다.

현재 권장 운영 구조는 다음과 같습니다.

```text
GitHub Actions
-> 1시간마다 가격 체크 실행
-> Turso 클라우드 DB에 가격 기록 저장
-> 필요 시 Discord 알림 전송

로컬 PC / 노트북
-> FastAPI 웹 서버 실행
-> 가격 현황, 실행 상태, 상품 관리 화면 확인
```

로컬 개발용 SQLite도 계속 지원합니다. 개발 중에는 `price_tracker.db`를 사용하고, 실제 자동 수집은 Turso DB에 쌓는 방식으로 운영할 수 있습니다.

## 프로젝트 목표

이 프로젝트의 목표는 단순히 가격을 한 번 가져오는 것이 아니라, 시간이 지날수록 의미가 생기는 가격 이력을 안정적으로 쌓고 확인하는 것입니다.

```text
가격 자동 수집
-> 가격 이력 저장
-> 목표가 도달 여부 확인
-> 실행 성공/실패 상태 추적
-> 웹 대시보드에서 조회
-> PC가 꺼져 있어도 클라우드에서 자동 실행
```

## 주요 기능

- `products.json`에 등록된 상품 가격 수집
- 다나와 상품 페이지에서 가격 크롤링
- SQLite 또는 Turso 클라우드 DB에 가격 기록 저장
- 목표가 도달 또는 가격 변경 시 Discord 알림 전송
- 가격 체크 실행 기록 저장
- 상품별 마지막 성공/실패 상태 저장
- 연속 실패 횟수 추적
- 브라우저 대시보드 제공
- 상품 추가, 수정, 삭제 관리 화면 제공
- GitHub Actions를 통한 1시간 주기 자동 실행

## 기술 스택

```text
Backend
= Python, FastAPI

Crawling
= requests, BeautifulSoup

Database
= SQLite, Turso/libSQL

Automation
= GitHub Actions, Windows 작업 스케줄러

Notification
= Discord Webhook

Frontend
= FastAPI HTML Response 기반 대시보드
```

## 주요 화면

현재 웹 UI는 FastAPI에서 HTML을 직접 반환하는 방식으로 구성되어 있습니다.

| 화면 | 경로 | 역할 |
| --- | --- | --- |
| 대시보드 | `/` | 최신가, 목표가, 최저가, 추세, 실행 상태, 상품별 실패 상태 확인 |
| 상품 관리 | `/manage` | 상품 추가, 수정, 삭제 및 목표가 변경 |
| API 문서 | `/docs` | FastAPI 자동 문서를 통한 API 확인 및 테스트 |
| 상태 API | `/status` | 전체 실행 상태와 상품별 실패 상태를 JSON으로 조회 |

## 설계 의도와 발전 과정

프로젝트는 사용하면서 생긴 문제를 하나씩 해결하는 방식으로 구조가 발전했습니다.

### 1. CSV 저장에서 SQLite 저장으로 전환

초기에는 상품별 가격을 CSV 파일로 저장했습니다.

하지만 상품 수가 늘어나면 파일이 여러 개로 나뉘고, 상품 정보와 가격 이력을 함께 관리하기 어려웠습니다.

이를 해결하기 위해 SQLite DB로 전환했습니다.

```text
CSV 파일 저장
-> 상품별 파일 관리가 복잡함
-> 가격 이력 조회와 요약이 불편함
-> SQLite로 전환
```

### 2. 로컬 DB에서 Turso 클라우드 DB로 확장

SQLite는 개발과 로컬 실행에는 편하지만, 노트북과 데스크탑에서 각각 실행하면 DB가 따로 쌓이는 문제가 있었습니다.

또한 PC가 꺼져 있으면 가격 기록이 쌓이지 않았습니다.

이를 해결하기 위해 Turso 클라우드 DB를 추가했습니다.

```text
로컬 SQLite
-> 실행한 컴퓨터에만 기록 저장
-> 사용 환경이 나뉘면 DB도 나뉨
-> Turso 클라우드 DB 도입
-> GitHub Actions, 로컬 API, 개발환경이 같은 DB를 볼 수 있음
```

### 3. while 루프에서 작업 스케줄러, GitHub Actions로 전환

초기에는 `main.py --monitor`가 while 루프로 계속 실행되며 가격을 확인했습니다.

이 방식은 단순하지만, 터미널이나 PC가 꺼지면 수집이 멈춥니다.

이후 Windows 작업 스케줄러를 검토했고, 최종적으로 PC가 꺼져 있어도 실행될 수 있도록 GitHub Actions scheduled workflow를 추가했습니다.

```text
while 루프 기반 monitor
-> PC가 켜져 있어야 함
-> Windows 작업 스케줄러로 로컬 자동 실행 준비
-> GitHub Actions로 클라우드 자동 실행
-> 1시간마다 main.py --once 실행
```

### 4. 직접 JSON 수정에서 웹 상품 관리로 개선

처음에는 `products.json`을 직접 수정해야 상품을 추가하거나 목표가를 바꿀 수 있었습니다.

현재는 `/manage` 화면에서 상품 추가, 수정, 삭제가 가능합니다.

삭제 시 가격 이력은 보존하고, DB에서는 `is_active = 0`으로 비활성화합니다.

```text
products.json 직접 수정
-> 웹 상품 관리 화면 추가
-> 추가 / 수정 / 삭제 가능
-> 삭제된 상품의 과거 가격 기록은 보존
```

### 5. 조용한 실패를 줄이기 위한 운영 상태 기록 추가

가격 추적기는 실패해도 조용히 멈추면 의미가 없습니다.

이를 줄이기 위해 전체 실행 기록과 상품별 마지막 성공/실패 상태를 저장합니다.

```text
check_runs
= 전체 가격 체크 실행 기록

product_check_status
= 상품별 마지막 성공/실패 상태
= 연속 실패 횟수
= 마지막 에러 메시지
```

## 현재 구조

```text
products.json
-> 추적할 상품 목록

main.py --once
-> 상품 가격을 한 번 확인
-> DB에 가격 기록 저장
-> 필요 시 Discord 알림 전송

main.py --monitor
-> 로컬에서 계속 가격 확인 반복

main.py --api
-> FastAPI 웹 화면 실행

GitHub Actions
-> 1시간마다 main.py --once 실행
-> Turso DB에 기록
```

역할을 파일 기준으로 나누면 다음과 같습니다.

```text
main.py
= 실행 모드를 선택하는 진입점

app/config.py
= .env와 환경변수 설정 로드

app/crawler.py
= 다나와 상품 페이지에서 가격 가져오기

app/storage.py
= SQLite 또는 Turso DB 저장 및 조회

app/scheduler.py
= 상품 목록을 읽고 가격 체크 흐름 실행

app/products_config.py
= products.json 읽기, 저장, 검증, 상품 추가/수정/삭제

app/notifier.py
= Discord 알림 전송

app/api.py
= 대시보드, 상품 관리 화면, API 제공

products.json
= 추적할 상품 목록 원본
```

## 폴더 구조

```text
SSD_price_tracker/
  main.py
  products.json
  requirements.txt
  README.md
  .env.example
  .github/
    workflows/
      price-check.yml
  app/
    api.py
    config.py
    crawler.py
    notifier.py
    products_config.py
    scheduler.py
    storage.py
  scripts/
    migrate_csv_to_sqlite.py
    register_api_task.ps1
```

## 설치 방법

가상환경을 생성합니다.

```bash
python -m venv venv
```

가상환경을 활성화합니다.

```bash
.\venv\Scripts\activate
```

필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 참고해서 `.env` 파일을 만듭니다.

```text
DISCORD_WEBHOOK_URL=your_discord_webhook_url
API_HOST=127.0.0.1
API_PORT=8000
DATABASE_BACKEND=sqlite
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=
CHECK_INTERVAL_SECONDS=3600
REQUEST_DELAY_SECONDS=3
FAILURE_ALERT_THRESHOLD=3
```

각 값의 의미는 다음과 같습니다.

```text
DISCORD_WEBHOOK_URL
= Discord 알림을 받을 웹훅 주소

API_HOST
= 웹 API 서버를 열 주소

API_PORT
= 웹 API 서버 포트

DATABASE_BACKEND
= sqlite 또는 turso

TURSO_DATABASE_URL
= Turso DB URL

TURSO_AUTH_TOKEN
= Turso 인증 토큰

CHECK_INTERVAL_SECONDS
= --monitor 모드에서 다음 체크까지 기다리는 시간

REQUEST_DELAY_SECONDS
= 상품 하나를 확인한 뒤 다음 상품으로 넘어가기 전 대기 시간

FAILURE_ALERT_THRESHOLD
= 상품별 연속 실패 알림 기준 횟수
```

로컬 개발만 할 경우에는 기본값처럼 SQLite를 사용하면 됩니다.

```text
DATABASE_BACKEND=sqlite
```

Turso 클라우드 DB를 사용할 경우에는 다음처럼 설정합니다.

```text
DATABASE_BACKEND=turso
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
```

토큰은 Git에 커밋하지 않습니다. `.env`는 `.gitignore`에 포함되어 있습니다.

## 상품 설정

추적할 상품은 `products.json`에서 관리합니다.

```json
[
  {
    "name": "WD_BLACK_SN850X_2TB",
    "url": "https://prod.danawa.com/info/?pcode=17788451",
    "target_price": 520000
  }
]
```

각 값의 의미는 다음과 같습니다.

```text
name
= 상품 이름

url
= 다나와 상품 URL

target_price
= 목표 가격
```

웹 관리 화면에서도 상품을 추가, 수정, 삭제할 수 있습니다.

```text
http://127.0.0.1:8000/manage
```

현재는 `products.json`이 상품 목록의 원본입니다. `/manage`에서 상품을 바꾸면 로컬 `products.json`이 수정됩니다.

GitHub Actions 자동 실행에 상품 변경을 반영하려면 `products.json` 변경사항을 커밋하고 GitHub에 push해야 합니다.

```text
/manage에서 상품 변경
-> products.json 변경
-> git commit / push
-> GitHub Actions 자동 실행에 반영
```

## 실행 방법

### 가격 한 번 수집

```bash
.\venv\Scripts\python.exe main.py --once
```

실행 흐름:

```text
products.json 읽기
-> 상품별 URL 접속
-> 가격 크롤링
-> DB 저장
-> 실행 상태 저장
-> 필요 시 Discord 알림
-> 종료
```

### 가격 계속 감시

```bash
.\venv\Scripts\python.exe main.py --monitor
```

실행 흐름:

```text
가격 수집
-> CHECK_INTERVAL_SECONDS 만큼 대기
-> 다시 가격 수집
-> 반복
```

이 모드는 PC가 켜져 있을 때만 동작합니다. PC가 꺼져 있어도 로그가 쌓이게 하려면 GitHub Actions + Turso 구성을 사용합니다.

### 웹 API 서버 실행

```bash
.\venv\Scripts\python.exe main.py --api
```

대시보드:

```text
http://127.0.0.1:8000/
```

상품 관리:

```text
http://127.0.0.1:8000/manage
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

## 웹 화면

### `/`

가격 현황을 확인하는 메인 대시보드입니다.

표시 항목:

```text
Last Run
Success
Failures
Products
Product
Latest
Target
Lowest
Trend
Checked At
Failures
Health
Target
```

시간 값은 KST 기준으로 표시됩니다.

`Health`는 상품별 크롤링 상태를 의미합니다.

```text
Pending
= 아직 상태 체크 기록 없음

Healthy
= 최근 체크 성공

Failing
= 최근 체크 실패 또는 연속 실패 있음
```

### `/manage`

상품 관리 화면입니다.

가능한 작업:

```text
상품 추가
상품명 수정
URL 수정
목표가 수정
상품 삭제
```

삭제 버튼을 누르면 `products.json`에서는 상품이 제거됩니다.

DB에서는 가격 이력을 지우지 않고 `is_active = 0`으로 비활성화합니다.

```text
products.json
-> 상품 제거

products 테이블
-> is_active = 0

price_records 테이블
-> 기존 가격 이력 유지
```

즉, 화면에서는 삭제된 것처럼 보이지만 과거 가격 기록은 보존됩니다.

## 운영 상태 기록

가격 추적기는 조용히 실패하면 의미가 없어지기 때문에, 가격 기록과 별도로 실행 상태를 저장합니다.

저장되는 상태:

```text
전체 실행 기록
= 언제 시작했고 끝났는지
= 몇 개 상품을 확인했는지
= 성공/실패 개수
= 전체 실행 상태

상품별 상태
= 마지막 체크 시간
= 마지막 성공 시간
= 마지막 실패 시간
= 마지막 에러 메시지
= 연속 실패 횟수
```

대시보드에서는 이 정보를 바탕으로 `Healthy`, `Failing`, `Pending` 상태를 보여줍니다.

연속 실패 횟수가 `FAILURE_ALERT_THRESHOLD`에 도달하면 Discord 경고를 보낼 수 있습니다.

### `/docs`

FastAPI가 자동으로 만들어주는 API 테스트 문서입니다.

실제 사용자 화면이 아니라, API 주소를 확인하고 직접 실행해볼 수 있는 개발자용 화면입니다.

## 주요 API

```text
GET /
= 가격 요약 HTML 화면

GET /manage
= 상품 관리 HTML 화면

GET /health
= API 상태 확인

GET /status
= 전체 실행 상태와 상품별 실패 상태 조회

GET /products
= 활성 상품 목록 조회

GET /products/{product_id}
= 특정 활성 상품 조회

GET /products/{product_id}/prices
= 특정 상품의 가격 기록 조회

GET /summary
= 상품별 가격 요약 조회

POST /check-now
= 전체 상품 즉시 가격 체크
```

## 데이터 저장 방식

DB는 두 가지 모드를 지원합니다.

```text
sqlite
= 로컬 개발용 price_tracker.db 사용

turso
= Turso 클라우드 DB 사용
```

주요 테이블:

```text
products
= 상품 정보

price_records
= 상품별 가격 기록

check_runs
= 전체 가격 체크 실행 기록

product_check_status
= 상품별 마지막 성공/실패 상태
```

관계는 다음과 같습니다.

```text
products 1개
-> price_records 여러 개
```

`products.json`과 DB의 역할은 다릅니다.

```text
products.json
= 추적할 상품 목록 원본

products 테이블
= 가격 기록과 상태 기록을 연결하기 위한 DB 내부 상품 정보
```

## GitHub Actions 자동 실행

자동 가격 체크 workflow는 다음 파일에 있습니다.

```text
.github/workflows/price-check.yml
```

실행 조건:

```yaml
on:
  schedule:
    - cron: "17 * * * *"
  workflow_dispatch:
```

의미:

```text
매시간 17분에 자동 실행
수동 실행 가능
```

실행 명령:

```bash
python main.py --once
```

GitHub Actions는 새 runner에서 실행되므로, 매번 checkout, Python 설정, 패키지 설치 후 가격 체크를 실행합니다. 그래서 로컬 실행보다 느릴 수 있고, 예약 시간보다 몇 분 늦게 시작될 수 있습니다.

### GitHub Secrets

GitHub Actions에서 Turso DB를 사용하려면 repository secret을 등록해야 합니다.

GitHub 저장소에서 다음 경로로 이동합니다.

```text
Settings
-> Secrets and variables
-> Actions
-> New repository secret
```

필수 Secret:

```text
Name:
TURSO_DATABASE_URL

Secret:
libsql://...
```

```text
Name:
TURSO_AUTH_TOKEN

Secret:
eyJ...
```

선택 Secret:

```text
Name:
DISCORD_WEBHOOK_URL

Secret:
https://discord.com/api/webhooks/...
```

Secret 값에는 `.env`처럼 `KEY=value` 전체를 넣지 않습니다.

잘못된 예:

```text
TURSO_AUTH_TOKEN=eyJ...
```

올바른 예:

```text
eyJ...
```

토큰은 한 줄로 넣고, 따옴표나 줄바꿈을 포함하지 않습니다.

## 데스크탑 서버 방식

현재는 GitHub Actions + Turso가 권장 운영 방식입니다.

다만 로컬 네트워크에서 데스크탑을 메인 서버로 쓰는 방식도 가능합니다.

```text
데스크탑
= 가격 수집
= DB 보관
= API 서버 실행

노트북
= 코드 개발
= 브라우저로 데스크탑 API 접속
```

데스크탑에서 노트북 접속을 허용하려면 데스크탑 `.env`를 다음처럼 설정합니다.

```text
API_HOST=0.0.0.0
API_PORT=8000
```

데스크탑에서 API 서버를 실행합니다.

```bash
.\venv\Scripts\python.exe main.py --api
```

노트북에서는 데스크탑의 내부 IP 주소로 접속합니다.

```text
http://데스크탑_IP주소:8000/
```

주의할 점:

```text
같은 인터넷을 사용해도 같은 내부망이 아닐 수 있습니다.
데스크탑 이더넷과 노트북 Wi-Fi가 서로 다른 IP 대역이면 접속이 안 될 수 있습니다.
```

이 경우 데스크탑 Wi-Fi를 켜고 노트북과 같은 Wi-Fi에 연결한 뒤, 데스크탑 Wi-Fi IPv4 주소로 접속합니다.

```text
http://데스크탑_WiFi_IP:8000/
```

## Windows 작업 스케줄러

API 서버 자동 실행에는 다음 파일을 사용할 수 있습니다.

```text
run_api.ps1
scripts/register_api_task.ps1
```

관리자 권한 PowerShell에서 다음 스크립트를 실행하면 작업 스케줄러에 API 자동 실행 작업을 등록할 수 있습니다.

```powershell
.\scripts\register_api_task.ps1
```

직접 작업 스케줄러에서 등록한다면 동작은 다음처럼 설정합니다.

```text
프로그램
= C:\Users\godae\SSD_price_tracker\venv\Scripts\python.exe

인수
= main.py --api

시작 위치
= C:\Users\godae\SSD_price_tracker
```

`--once`와 `--api`는 스케줄러 설정 방식이 다릅니다.

```text
main.py --once
= 실행 후 종료
= 시간 반복 실행 가능

main.py --api
= 계속 실행되는 서버
= 로그온 시 1회 실행 권장
```

## CSV 마이그레이션

기존 CSV 데이터를 SQLite로 옮기려면 다음 명령어를 실행합니다.

```bash
.\venv\Scripts\python.exe scripts\migrate_csv_to_sqlite.py
```

마이그레이션은 중복 저장을 방지하도록 구성되어 있습니다.

## 자주 만난 오류

### 가격 체크가 실행됐는지 알 수 없는 경우

대시보드 상단의 실행 상태를 먼저 확인합니다.

```text
Last Run
Success
Failures
Products
```

상품별 상태는 `Health`와 `Failures` 컬럼에서 확인합니다.

```text
Healthy
= 최근 체크 성공

Failing
= 최근 체크 실패 또는 연속 실패 있음

Pending
= 아직 체크 기록 없음
```

JSON으로 확인하려면 다음 API를 사용합니다.

```text
GET /status
```

### `main.py --api`를 실행했는데 터미널이 멈춘 것처럼 보이는 경우

정상 동작입니다.

API 서버는 계속 켜져 있어야 브라우저에서 접속할 수 있습니다.

서버를 종료하려면 터미널에서 `Ctrl + C`를 누릅니다.

### `/docs`에 가격표가 바로 안 보이는 경우

`/docs`는 사용자 화면이 아니라 API 테스트 화면입니다.

가격표를 보려면 다음 주소로 접속합니다.

```text
http://127.0.0.1:8000/
```

상품 관리 화면은 다음 주소입니다.

```text
http://127.0.0.1:8000/manage
```

### 8000번 포트 중복 오류

```text
[Errno 10048]
```

이미 API 서버가 켜져 있을 때 발생합니다.

확인:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

남아 있는 Python 프로세스 확인:

```powershell
Get-Process python,python3,uvicorn -ErrorAction SilentlyContinue
```

필요하면 해당 PID를 종료합니다.

```powershell
Stop-Process -Id <PID> -Force
```

### 노트북에서 데스크탑 API에 접속할 수 없는 경우

데스크탑 브라우저에서는 API가 열리는데 노트북에서 접속되지 않는 경우가 있습니다.

먼저 데스크탑 `.env`에 외부 접속 허용 설정이 되어 있어야 합니다.

```text
API_HOST=0.0.0.0
API_PORT=8000
```

API 서버를 다시 시작한 뒤 데스크탑에서 8000번 포트가 열려 있는지 확인합니다.

```powershell
netstat -ano | findstr :8000
```

정상 예시:

```text
0.0.0.0:8000 LISTENING
```

그 다음 데스크탑과 노트북이 같은 내부망인지 확인합니다.

```powershell
ipconfig
```

예를 들어 데스크탑은 모뎀 쪽 이더넷에 연결되어 있고, 노트북은 공유기 Wi-Fi에 연결되어 있으면 서로 다른 내부망일 수 있습니다.

```text
데스크탑
= 192.168.55.xxx

노트북
= 192.168.45.xxx
```

이 경우 같은 인터넷을 쓰는 것처럼 보여도 노트북에서 데스크탑 API에 접속하거나 `ping`을 보내는 것이 실패할 수 있습니다.

해결 방법은 데스크탑 Wi-Fi를 켜고 노트북과 같은 Wi-Fi에 연결한 뒤, 데스크탑의 Wi-Fi IPv4 주소로 접속하는 것입니다.

```text
http://데스크탑_WiFi_IP:8000/
```

같은 대역이고 `ping`도 되는데 접속이 안 되면 Windows 방화벽에서 TCP 8000번 포트가 막혔을 가능성이 있습니다.

### `/manage`에서 상품을 바꿨는데 GitHub Actions에 반영되지 않는 경우

현재 상품 목록의 원본은 `products.json`입니다.

로컬 `/manage`에서 상품을 추가, 수정, 삭제하면 로컬의 `products.json`만 바뀝니다.

GitHub Actions는 GitHub에 올라간 `products.json`을 읽기 때문에, 변경사항을 자동 실행에 반영하려면 커밋하고 push해야 합니다.

```text
/manage에서 상품 변경
-> products.json 변경
-> git commit
-> git push
-> GitHub Actions에 반영
```

### GitHub Actions에서 Turso 값이 비어 있는 경우

에러 예시:

```text
RuntimeError: Turso database requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.
```

원인:

```text
GitHub Secrets에 TURSO_DATABASE_URL 또는 TURSO_AUTH_TOKEN이 등록되지 않았거나 이름이 다름
```

해결:

```text
Settings
-> Secrets and variables
-> Actions
```

에서 정확한 이름으로 Secret을 등록합니다.

GitHub Secret은 `.env`처럼 전체 줄을 넣는 방식이 아닙니다.

잘못된 예:

```text
TURSO_DATABASE_URL=libsql://...
```

올바른 예:

```text
Name:
TURSO_DATABASE_URL

Secret:
libsql://...
```

### Hrana InvalidHeaderValue 오류

에러 예시:

```text
ValueError: Hrana: http error: InvalidHeaderValue
```

원인:

```text
TURSO_AUTH_TOKEN 값에 접두어, 따옴표, 줄바꿈, 공백 등이 포함됨
```

잘못된 예:

```text
TURSO_AUTH_TOKEN=eyJ...
```

올바른 예:

```text
eyJ...
```

값에는 따옴표를 넣지 않고, 한 줄로 저장합니다.

## Git 관리

`price_tracker.db`는 실행 결과로 생성되는 로컬 데이터이므로 Git에 커밋하지 않습니다.

커밋해야 하는 것:

```text
코드 변경
products.json 변경
README.md 변경
workflow 변경
```

커밋하지 않는 것:

```text
.env
price_tracker.db
venv/
```

GitHub Actions가 보는 상품 목록은 GitHub에 올라간 `products.json`입니다.

따라서 `/manage`에서 상품을 바꾼 뒤 자동 실행에 반영하려면 `products.json`을 커밋하고 push해야 합니다.

## 한계와 개선 계획

현재 상품 목록의 원본은 `products.json`입니다.

웹 관리 화면에서 상품을 추가, 수정, 삭제할 수는 있지만, GitHub Actions 자동 실행에 반영하려면 변경된 `products.json`을 다시 커밋하고 push해야 합니다.

이 구조는 단순하고 Git으로 변경 이력을 추적하기 쉽다는 장점이 있지만, 웹에서 수정한 상품이 클라우드 자동 실행에 즉시 반영되지 않는다는 한계가 있습니다.

향후에는 상품 목록의 기준을 DB로 전환해, 웹 관리 화면에서 수정한 내용이 GitHub Actions 자동 수집에도 바로 반영되도록 개선할 계획입니다.

추가 개선 계획:

```text
상품별 상세 페이지 추가
가격 이력 큰 그래프 추가
상품별 즉시 체크 추가
알림 중복 방지 및 정책 개선
README에 실제 대시보드/상품 관리 화면 스크린샷 추가
```

## 운영 흐름 요약

현재 가장 안정적인 운영 흐름은 다음과 같습니다.

```text
1. products.json에 추적 상품 등록
2. GitHub에 push
3. GitHub Actions가 1시간마다 가격 체크
4. Turso DB에 가격 기록 저장
5. 로컬에서 main.py --api 실행
6. 브라우저에서 대시보드와 상품 관리 화면 확인
```

이 구조를 통해 PC가 꺼져 있어도 가격 로그가 계속 쌓일 수 있습니다.
