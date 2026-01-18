import requests
import json

# あなたのAPIキー（eyJ...）をここに貼る
API_KEY = "DvDJzTQ3bOcBNofUi_-xo2xroR55sdggOiWtPgXvASo"

# 【修正】V2の正しい株価取得エンドポイント
# パスが /equities/bars/daily に変わりました
url = "https://api.jquants.com/v2/equities/bars/daily?code=8058"

headers = {
    "x-api-key": API_KEY
}

print("V2 API 正式エンドポイントでテスト開始...")
try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("✅ 接続成功！")
        data = response.json()
        # V2ではデータの構造も少し変わっています
        if "daily_quotes" in data:
            print(f"最新データ: {data['daily_quotes'][-1]}")
        else:
            print(f"取得結果: {data}")
    else:
        print(f"❌ 接続失敗: {response.status_code}")
        print(f"エラー内容: {response.text}")
except Exception as e:
    print(f"通信エラー: {e}")