## 타깃 아이템 정하기

SSD, SD카드

ai 수요 증가에 따라 보조 메모리 가격이 가파르게 폭등하는 중이어서 로그를 파악하고자 한다

*여러 SSD 상품의 가격을 주기적으로 수집하고, 가격 이력을 저장하며, 목표가 도달 시 알림을 보내는 백엔드 기반 가격 모니터링 서비스*

- 2026/05/06
    - **주요 성과**
        - `requests`, `bs4` 활용 및 로컬 파일 시스템 저장 성공
        
        ![image.png](attachment:0529a0b1-2db7-4de6-b21b-208a96f22fae:image.png)
        
    - **핵심 로직**
        - **`get_price()`**
            - `requests`를 이용한 HTTP 통신 및 `User-Agent` 헤더 적용(안티 크롤링 우회)
            - `BeautifulSoup`의 CSS Selector를 활용한 특정 데이터 타격
            - 문자열(String) 데이터를 연산 가능한 정수형(Integer)으로 정제
        - **`save_to_csv()`**
            - 데이터 영속성(Persistence) 확보를 위한 파일 입출력 구현
            - `mode='a'`(Append)를 통한 기존 데이터 보존 및 누적 기록
            - `datetime` 라이브러리를 활용한 타임스탬프 생성
    - **트러블슈팅**
        - **이슈 1: 윈도우 스크립트 실행 권한 문제**
            - 원인: PowerShell 보안 정책으로 인한 가상환경 활성화 차단
            - 해결: `Set-ExecutionPolicy` 설정을 통한 권한 부여
        - **이슈 2: GitHub 동기화 경로 문제**
            - 원인: 로컬 폴더 구조와 리포지토리 폴더 구조 불일치로 인한 파일 유실
            - 해결: 폴더 이동 및 GitHub Desktop을 이용한 정확한 Clone/Push 프로세스 확립
        - **이슈 3: 서버 차단(403 Forbidden) 및 데이터 왜곡**
            - 원인: 서버의 봇 감지 및 엑셀의 데이터 표시 방식(인코딩/셀 너비) 차이
            - 해결: `User-Agent` 설정 및 `utf-8-sig` 인코딩 적용. 메모장을 통한 원본 데이터 검증
- 2026/05/13
    - **주요 성과**
        - 다중 품목 실시간 감시 및 조건부 알림 자동화 시스템 완성
            
            ![image.png](attachment:350f4d94-0c75-4f80-af50-5c0e9aa592e9:5afe5848-89c7-4035-84a6-0190587cbc28.png)
            
        - JSON 설정을 통한 확장성 확보 및 디스코드 연동을 통한 실시간 모니터링 환경 구축
            
            ```json
            [
                {
                    "name": "WD_BLACK_SN850X_2TB",
                    "url": "https://prod.danawa.com/info/?pcode=17788451",
                    "target_price": 520000
                },
                {
                    "name": "SK_Hynix_P41_2TB",
                    "url": "https://prod.danawa.com/info/?pcode=17000984",
                    "target_price": 620000
            
                },
                {
                    "name": "SK_Hynix_P51_2TB",
                    "url": "https://prod.danawa.com/info/?pcode=72823133",
                    "target_price": 850000
                },
                {
                    "name": "Samsung_990_EVO_Plus_2TB",
                    "url": "https://prod.danawa.com/info/?pcode=69869573",
                    "target_price": 550000
                }
            ]
            ```
            
    - **핵심 로직**
        - ****`main()` & `products.json`
            - 외부 설정 기반 관리: 소스 코드 수정 없이 감시 대상을 추가/삭제할 수 있는 데이터 중심(Data-driven) 구조 설계
            - Polling Loop: `while` 루프와 `time.sleep`을 조합하여 24시간 상주 가능한 자동화 엔진 구현
        - `save_to_csv()` & `get_last_price()` (업그레이드)
            - 동적 파일 핸들링: 상품별 고유 ID(`name`)를 기반으로 개별 CSV 파일을 생성하여 데이터 간 간섭 방지
            - Header Management: `os.path.exists`를 활용해 파일 생성 시에만 제목줄(Header)을 삽입하는 예외 처리 로직 추가
            - 상태 유지(State): 이전 가격 데이터를 로드하여 현재가와 비교함으로써 불필요한 중복 데이터 기록 방지
        - 조건부 알림 로직
            - 이중 검문 시스템: '단순 가격 변동'과 '목표가(`target_price`) 도달' 상황을 분리하여 메시지 강도를 차별화
            - Discord Webhook: `requests.post`를 활용한 외부 메신저 연동으로 즉각적인 의사결정 지원
    - **트러블슈팅**
        - **이슈 1: VS Code 인터프리터 참조 오류**
            - 원인: 가상환경(`venv`)이 아닌 전역 파이썬 환경이 활성화되어 설치된 라이브러리를 인식하지 못함
            - 해결: `Select Interpreter` 설정을 통해 프로젝트 내부 가상환경 경로로 수동 지정하여 환경 동기화
        - **이슈 2: 논리적 조건문에 의한 알림 미발송**
            - 원인: `if current_price != last_price` 로직으로 인해 테스트 시 가격 변동이 없으면 알림 함수가 호출되지 않음
            - 해결: CSV 데이터를 수동으로 수정하여 인위적인 변동 상황을 생성, 전체 로직의 정상 작동 유무를 검증함
        - **이슈 3: `try...except`를 통한 Fault Tolerance 확보**
            - 원인: 특정 상품의 크롤링 에러(서버 응답 지연 등) 발생 시 프로그램 전체가 종료되는 리스크 발견
            - 해결: 개별 품목 루프 내부에 예외 처리 블록을 배치하여, 특정 타겟의 장애가 전체 시스템에 영향을 주지 않도록 설계