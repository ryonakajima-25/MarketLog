# app.py
import streamlit as st
from datetime import datetime
import data_manager

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# 設定
st.set_page_config(page_title="market-log", layout="wide")
local_css("style.css")

st.title("📊 market-log")
# 【修正】Lightプラン用の表示に変更
st.caption("✅ J-Quants API (Light Plan) Connected")

# 開発モードの切り替え
is_dev_mode = st.sidebar.toggle("開発モード（モック使用）", value=False)
API_KEY = st.secrets["JQUANTS_API_KEY"]

@st.cache_data(ttl=60)
def get_data(code, is_dev):
    if is_dev:
        return data_manager.get_mock_data(code), None
    else:
        return data_manager.fetch_real_data(code, API_KEY)

def display_stock_metric(container, code, name):
    df, err = get_data(code, is_dev_mode)
    with container:
        st.markdown(f"### {name} ({code})")
        if df is not None:
            # 最新の行を取得
            latest = df.iloc[-1]
            date_str = latest['Date']
            close_price = int(latest['Close'])
            
            # 前日比の計算（データが2件以上ある場合のみ）
            diff = 0
            if len(df) >= 2:
                prev = df.iloc[-2]
                diff = close_price - int(prev['Close'])
            
            st.caption(f"📅 {date_str}")
            st.metric(label="終値", value=f"¥{close_price:,}", delta=f"¥{diff:,}")
        else:
            if err:
                st.error(f"取得失敗: {err}")
            else:
                st.info("データなし")

# --- メインエリア ---

st.subheader("🔍 銘柄検索")
search_query = st.text_input("銘柄コード または 名称を入力してください（例: 8058, 三菱商事）")

target_stocks = {
    "3350": "メタプラネット",
    "8058": "三菱商事"
}

if search_query:
    search_code = None
    search_name = "検索結果"

    # A. 名称検索
    found_code = [k for k, v in target_stocks.items() if v == search_query]
    if found_code:
        search_code = found_code[0]
        search_name = target_stocks[search_code]
    
    # B. コード検索
    elif search_query.isdigit() and len(search_query) == 4:
        search_code = search_query
        search_name = f"コード: {search_code}"
    
    else:
        st.error("⚠️ 正しい銘柄コード(4桁)か、登録済みの名称を入力してください。")

    if search_code:
        # 【重要】エラー回避のため st.container() を渡す
        target_container = st.container()
        display_stock_metric(target_container, search_code, search_name)

st.divider()

st.subheader("📈 定点観測")
cols = st.columns(len(target_stocks))

for col, (code, name) in zip(cols, target_stocks.items()):
    display_stock_metric(col, code, name)