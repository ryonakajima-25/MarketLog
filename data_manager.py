import pandas as pd
import requests

def fetch_real_data(code, api_key):
    # 1. 必ず5桁にする（4桁なら0を足す）
    target_code = str(code) + "0" if len(str(code)) == 4 else str(code)
    
    # 2. 【重要】Freeプランで確実にデータがある「過去の期間」を固定指定
    # 日付を指定しないと「今日」を見に行ってしまい、Freeプランでは空になります
    start_date = "2025-05-01"
    end_date = "2025-05-30"
    
    url = f"https://api.jquants.com/v2/equities/bars/daily?code={target_code}&from={start_date}&to={end_date}"
    headers = {"x-api-key": api_key.strip()}
    
    print(f"\n--- 🚀 API Request: {target_code} (Fixed Date: 2025/05) ---")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        # 429エラー対策
        if response.status_code == 429:
            print("❌ Error 429: Rate limit exceeded.")
            return None, "API制限中（時間を空けてください）"

        res_json = response.json()
        
        if response.status_code == 200:
            quotes = res_json.get("daily_quotes", [])
            if len(quotes) > 0:
                df = pd.DataFrame(quotes)
                latest = df.iloc[-1]
                print(f"✅ Success: {target_code} - {len(df)}件 (Latest: {latest['Date']} ¥{latest['Close']})")
                return df, None
            else:
                print(f"⚠️ Empty: {target_code} のデータが空でした")
                return None, "データなし（期間指定を見直してください）"
        else:
            print(f"❌ API Error: {response.status_code} - {res_json}")
            return None, f"API Error: {response.status_code}"
            
    except Exception as e:
        print(f"🚨 Exception: {str(e)}")
        return None, str(e)

def get_mock_data(code):
    """開発用のダミーデータ"""
    data = [{"Date": "2026-01-16", "Close": 526.0, "Open": 500.0, "High": 550.0, "Low": 490.0}]
    return pd.DataFrame(data)