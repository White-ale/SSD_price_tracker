# SSD Price Tracker

SSD 가격을 주기적으로 확인하고, 가격 이력을 SQLite에 저장한 뒤 웹에서 조회할 수 있는 로컬 가격 추적 프로젝트입니다.

현재는 로컬 환경에서 실행하는 단계입니다.

## 주요 기능

- `products.json`에 등록된 상품 가격 수집
- SQLite DB에 상품 정보와 가격 기록 저장
- 목표가 도달 시 Discord 알림 전송
- FastAPI를 통한 가격 데이터 조회
- 브라우저에서 가격 요약 화면 확인

## 현재 실행 구조

```text
products.json
→ main.py --once / --monitor
→ app/crawler.py
→ app/storage.py
→ price_tracker.db
→ main.py --api
→ FastAPI 웹 화면
```

역할을 간단히 나누면 다음과 같습니다.

```text
main.py
= 실행 모드를 선택하는 진입점

app/crawler.py
= 다나와 상품 페이지에서 가격 가져오기

app/storage.py
= SQLite DB 저장 및 조회

app/scheduler.py
= 상품 목록을 읽고 가격 확인 흐름 실행

app/notifier.py
= Discord 알림 전송

app/api.py
= 웹 화면 및 API 제공

products.json
= 사람이 직접 수정하는 상품 설정 파일
```

## 폴더 구조

```text
SSD_price_tracker/
  main.py
  products.json
  requirements.txt
  README.md
  app/
    api.py
    config.py
    crawler.py
    notifier.py
    scheduler.py
    storage.py
  scripts/
    migrate_csv_to_sqlite.py
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
```

Discord 알림을 사용하지 않을 경우 비워둬도 됩니다.

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

## 실행 방법

### 가격 한 번 수집

```bash
.\venv\Scripts\python.exe main.py --once
```

실행 흐름:

```text
products.json 읽기
→ 상품별 URL 접속
→ 가격 크롤링
→ SQLite DB 저장
→ 필요 시 Discord 알림
→ 종료
```

### 가격 계속 감시

```bash
.\venv\Scripts\python.exe main.py --monitor
```

실행 흐름:

```text
가격 수집
→ 일정 시간 대기
→ 다시 가격 수집
→ 반복
```

### 웹 API 서버 실행

```bash
.\venv\Scripts\python.exe main.py --api
```

웹 화면:

```text
http://127.0.0.1:8000/
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

## FastAPI 화면 설명

### `/`

사람이 보기 쉬운 가격 요약 화면입니다.

표시 항목:

```text
Product
Latest
Target
Lowest
Checked At
Status
```

### `/docs`

FastAPI가 자동으로 만들어주는 API 테스트 문서입니다.

`/docs`는 실제 사용자 화면이 아니라, API가 어떤 주소를 제공하는지 확인하고 직접 실행해볼 수 있는 개발자용 화면입니다.

### `/summary`

상품별 최신가, 최저가, 최고가, 목표가 도달 여부를 JSON으로 반환합니다.

## 주요 API

```text
GET /
= 가격 요약 HTML 화면

GET /products
= 전체 상품 목록 조회

GET /products/{product_id}
= 특정 상품 조회

GET /products/{product_id}/prices
= 특정 상품의 가격 기록 조회

GET /summary
= 상품별 가격 요약 조회
```

## 데이터 저장 방식

가격 데이터는 SQLite DB에 저장됩니다.

```text
price_tracker.db
```

테이블 구조:

```text
products
price_records
```

`products`는 상품 정보를 저장하고, `price_records`는 상품별 가격 기록을 저장합니다.

```text
products 1개
→ price_records 여러 개
```

`products.json`과 DB의 역할은 다릅니다.

```text
products.json
= 사람이 직접 수정하는 상품 설정 원본

products 테이블
= 가격 기록과 연결하기 위해 DB 내부에서 사용하는 상품 정보
```

## CSV 마이그레이션

기존 CSV 데이터를 SQLite로 옮기려면 다음 명령어를 실행합니다.

```bash
.\venv\Scripts\python.exe scripts\migrate_csv_to_sqlite.py
```

마이그레이션은 중복 저장을 방지하도록 구성되어 있습니다.

## 로컬 실행 상태

현재 프로젝트는 로컬 실행용입니다.

```text
http://127.0.0.1:8000
```

`127.0.0.1`은 내 컴퓨터를 의미하므로, 다른 사람은 이 주소로 접속할 수 없습니다.

다른 사람도 접속할 수 있게 하려면 Render, Railway, Fly.io, AWS 같은 외부 서버에 배포해야 합니다.

## 자주 만난 오류

### 8000번 포트 중복 오류

```text
[Errno 10048]
```

이미 API 서버가 켜져 있을 때 발생합니다.

해결:

```text
기존 서버 터미널에서 Ctrl + C
```

그 다음 다시 실행합니다.

```bash
.\venv\Scripts\python.exe main.py --api
```

### `/docs`에 데이터가 바로 안 보이는 경우

`/docs`는 사용자 화면이 아니라 API 테스트 화면입니다.

가격표를 보려면 다음 주소로 접속합니다.

```text
http://127.0.0.1:8000/
```

### `main.py --api`를 실행했는데 터미널이 멈춘 것처럼 보이는 경우

정상 동작입니다.

API 서버는 계속 켜져 있어야 브라우저에서 접속할 수 있습니다.

서버를 종료하려면 터미널에서 `Ctrl + C`를 누릅니다.

## Git 관리

`price_tracker.db`는 실행 결과로 생성되는 로컬 데이터이므로 Git에 커밋하지 않습니다.

DB 구조를 만드는 코드는 `app/storage.py`에 포함되어 있으므로, 다른 환경에서도 프로그램을 실행하면 같은 테이블 구조를 만들 수 있습니다.

## 다음 목표

- README를 계속 초보자용으로 개선
- 웹 화면 디자인 개선
- 상품 추가/수정/삭제 API 검토
- 가격 변화 그래프 추가 검토
- 배포 방식 검토