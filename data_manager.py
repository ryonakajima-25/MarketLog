import pandas as pd
import requests
import json
from datetime import datetime, timedelta

def fetch_real_data(code, api_key):
    # 1. 必ず5桁にする
    target_code = str(code) + "0" if len(str(code)) == 4 else str(code)
    
    # 2. 日付範囲の設定（直近1週間）
    now = datetime.now()
    end_date = now.strftime("%Y%m%d")
    start_date = (now - timedelta(days=7)).strftime("%Y%m%d")
    
    url = f"https://api.jquants.com/v2/equities/bars/daily?code={target_code}&from={start_date}&to={end_date}"
    headers = {"x-api-key": api_key.strip()}
    
    print(f"\n--- 🚀 API Request: {target_code} ({start_date} - {end_date}) ---")
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            print("❌ Error 429: Rate limit exceeded.")
            return None, "API制限中"

        res_json = response.json()
        
        if response.status_code == 200:
            # v2対応: 'data' キーから取得
            quotes = res_json.get("daily_quotes", []) or res_json.get("data", [])
            
            if len(quotes) > 0:
                df = pd.DataFrame(quotes)
                
                # 【修正1】カラム名をアプリの仕様に合わせてリネームする
                rename_map = {
                    'C': 'Close',
                    'O': 'Open',
                    'H': 'High',
                    'L': 'Low',
                    'Vo': 'Volume',
                    'Date': 'Date' # そのまま
                }
                # 存在しないカラムがあってもエラーにならないよう errors='ignore' は使いませんが、
                # 必要なカラムだけリネームします
                df = df.rename(columns=rename_map)

                # 日付でソート
                df = df.sort_values('Date')
                
                # 【修正2】コンソールでの結果確認用ログ
                print("\n📊 --- Response Data Preview (Latest 3 rows) ---")
                print(df[['Date', 'Close', 'Open', 'High', 'Low']].tail(3).to_string(index=False))
                print("------------------------------------------------\n")

                latest = df.iloc[-1]
                print(f"✅ Success: {target_code} - {latest['Date']} ¥{latest['Close']}")
                return df, None
            else:
                print(f"⚠️ Empty: {target_code} のデータが空でした")
                return None, "データが見つかりませんでした"
        else:
            print(f"❌ API Error: {response.status_code} - {res_json}")
            return None, f"API Error: {response.status_code}"
            
    except Exception as e:
        import traceback
        traceback.print_exc() # 詳細なエラーログを表示
        print(f"🚨 Exception: {str(e)}")
        return None, str(e)

def get_mock_data(code):
    """開発用のダミーデータ"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = [
        {"Date": "2026-01-15", "Close": 520.0, "Open": 500.0, "High": 530.0, "Low": 490.0},
        {"Date": today, "Close": 540.0, "Open": 520.0, "High": 550.0, "Low": 515.0}
    ]
    return pd.DataFrame(data)