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