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

def get_last_price():
    file_name = 'price_history.csv'
    
    # 1. 파일이 아예 없는 경우 (처음 실행 시)
    if not os.path.exists(file_name):
        return 0
    
    try:
        with open(file_name, mode='r', encoding='utf-8-sig') as f:
            reader = list(csv.reader(f))
            # 2. 파일은 있지만 제목줄(Header)만 있는 경우
            if len(reader) <= 1:
                return 0
            # 3. 가장 마지막 줄의 두 번째 칸(가격)을 가져옴
            last_row = reader[-1]
            return int(last_row[1])
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return 0
    
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

def send_discord_message(msg):
    webhook_url = "https://discord.com/api/webhooks/1503924832776097873/Cp8oGyyP2HxGpxArjvyGu2f5T6lDlIfCvTaHkC5xl2TbZS-Tl0vlbraq91IbOzs7mKJy" 
    
    data = {
        "content": msg  # 보낼 내용
    }

    response = requests.post(webhook_url, json=data)
    
    if response.status_code == 204:
        print("🔔 디스코드 알림 전송 완료!")
    else:
        print(f"❌ 알림 전송 실패: {response.status_code}")

# [실행부]
current_price = get_price()
last_price = get_last_price()
target_price = 850000 # 내가 생각하는 '지름신' 가격

if current_price:
    # 1. 가격이 변했을 때만 CSV 저장 (기존 로직)
    if current_price != last_price:
        save_to_csv(current_price)
        
        # 2. 가격이 변했는데, 그게 내 목표가보다 낮다면? 알람!
        if current_price <= target_price:
            message = f"🔥 대박! 현재가 {current_price}원! (목표가 {target_price}원 이하)"
            send_discord_message(message)
        else:
            # 그냥 가격이 변하기만 했을 때 보고용 알람 (선택)
            send_discord_message(f"📢 가격 변동: {last_price} -> {current_price}")