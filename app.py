# app.py
import streamlit as st
from datetime import datetime
import data_manager  # 作成したファイルをインポート

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 設定
st.set_page_config(page_title="market-log", layout="wide")
local_css("style.css")

st.title("📊 market-log")
st.warning("⚠️ 現在はFreeプラン期間内（2025年10月）のデータを表示しています")

# 開発モードの切り替え
is_dev_mode = st.sidebar.toggle("開発モード（モック使用）", value=False)
API_KEY = st.secrets["JQUANTS_API_KEY"]

# app.py (データ取得部分)
@st.cache_data(ttl=60) # デバッグ中はキャッシュ時間を短く（60秒）設定
def get_data(code, is_dev):
    if is_dev:
        return data_manager.get_mock_data(code), None
    else:
        return data_manager.fetch_real_data(code, API_KEY)

# 表示
# app.py の target_stocks 定義部分

target_stocks = {
    "3350": "メタプラネット",  # 4桁のままでOK（内部で "33500" になります）
    "8058": "三菱商事"      # 4桁のままでOK（内部で "80580" になります）
    }
cols = st.columns(len(target_stocks))

# app.py (表示部分の抜粋)
for col, (code, name) in zip(cols, target_stocks.items()):
    df, err = get_data(code, is_dev_mode)
    with col:
        st.markdown(f"### {name}")
        if df is not None:
            latest = df.iloc[-1]
            # 取得したデータの日付を明示
            st.caption(f"📅 データ日付: {latest['Date']}")
            
            # 前日比の計算（データが2日分以上あれば）
            diff = 0
            if len(df) >= 2:
                diff = latest['Close'] - df.iloc[-2]['Close']
            
            st.metric(label="終値", value=f"¥{int(latest['Close']):,}", delta=f"¥{int(diff):,}")
        else:
            st.error(f"取得失敗: {err}")