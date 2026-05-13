import json
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import os
import time

url = "https://prod.danawa.com/info/?pcode=72823133"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def get_price(url):
    response = requests.get(url, headers=headers) #정보 요청
    response.raise_for_status() #예외처리
    soup = BeautifulSoup(response.text, 'html.parser') #텍스트를 파이썬에 맞는 트리구조로 변환
    price_tag = soup.select_one('.text__num') #여러 태그 중 원하는(가격)에 대한 정보만 가져오기

    if price_tag:
        return int(price_tag.text.strip().replace(',', ''))
    return None

def save_to_csv(name, price):
    filename = f"{name}.csv"
    file_exists = os.path.exists(filename)
    
    with open(filename, mode='a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        
        # 파일이 처음 만들어지는 거라면 제목줄 추가
        if not file_exists:
            writer.writerow(['Date', 'Price'])
            
        # 데이터 추가
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), price])
    print(f"[{name}] 저장 완료: {price}원")

def get_last_price(name):
    file_name = f"{name}.csv"
    
    if not os.path.exists(file_name):
        return 0
    
    try:
        with open(file_name, mode='r', encoding='utf-8-sig') as f:
            reader = list(csv.reader(f))

            if len(reader) <= 1:
                return 0

            last_row = reader[-1]
            return int(last_row[1])
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return 0

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

def main():
    # 1. 사냥 목록 불러오기
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    while True:
        print(f"\n--- {datetime.now().strftime('%H:%M:%S')} 전체 감시 시작 ---")
        
        for item in products:
            name = item['name']
            url = item['url']
            target_price = item['target_price']
            
            try:
                # ------------------------------------------------
                current_price = get_price(url)
                last_price = get_last_price(name)
                
                if current_price:
                    # [기록 로직] 가격이 변했을 때만 CSV 저장
                    if current_price != last_price:
                        save_to_csv(name, current_price)
                        
                        # [알림 로직] 변동이 있는데 타겟가보다 낮다면?
                        if current_price <= target_price:
                            msg = f"🚨 [특가] {name}\n현재가: {current_price}원 (목표: {target_price}원)"
                            send_discord_message(msg)
                        else:
                            msg = f"📢 [변동] {name}: {last_price} -> {current_price}"
                            send_discord_message(msg)
                    else:
                        print(f"[{name}] 변동 없음 ({current_price}원)")
                # ------------------------------------------------

            except Exception as e:
                print(f"🚨 [{name}] 감시 중 에러 발생: {e}")
            
            time.sleep(3) 

        print("\n--- 전체 체크 완료. 1시간 뒤 다시 시작합니다. ---")
        time.sleep(3600)

if __name__ == "__main__":
    main()