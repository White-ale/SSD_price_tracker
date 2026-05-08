## 타깃 아이템 정하기

SSD, SD카드

ai 수요 증가에 따라 보조 메모리 가격이 가파르게 폭등하는 중이어서 로그를 파악하고자 한다

[Products](https://www.notion.so/35869785fda280a68097c6dd690b0f4f?pvs=21)

[웹페이지 업로드 로그](https://www.notion.so/35869785fda280c68a64d6daba2596fe?pvs=21)

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
    
    ```python
    import requests
    from bs4 import BeautifulSoup
    import csv
    from datetime import datetime
    import os
    
    url = "https://prod.danawa.com/info/?pcode=72823133"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    def get_price():
        response = requests.get(url, headers=headers) #정보 제공 요청
        response.raise_for_status() #에러 발생시 실행 중지
        soup = BeautifulSoup(response.text, 'html.parser') #텍스트를 파이썬에 맞는 트리구조로 변환
        price_tag = soup.select_one('.text__num') #여러 태그 중 원하는(가격)에 대한 정보만 가져오기
    
        if price_tag:
            return int(price_tag.text.strip().replace(',', ''))
        return None
    
    def save_to_csv(price):
        file_name = 'price_history.csv'
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file_exists = os.path.isfile(file_name) #이미 있는 파일인지 검사
    
        with open(file_name, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Time', 'Price'])
            writer.writerow([now, price])
        
        print(f"[{now}] {price}원 저장 완료!")
        
    current_price = get_price()
    if current_price:
        save_to_csv(current_price)
    ```