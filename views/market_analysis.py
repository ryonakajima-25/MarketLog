import streamlit as st
import pandas as pd
import data_manager

# 重たい処理なのでキャッシュ時間を長く設定
@st.cache_data(ttl=3600*12, show_spinner="過去データを集計中...")
def get_market_history(api_key):
    return data_manager.fetch_market_history(api_key, days=14)

def render(api_key):
    st.title("🌏 市場分析 (Light)")
    st.caption("※ Lightプランで取得可能な全銘柄データを独自集計して表示します")

    # 1. 市場概況 (日次)
    df_market, err = data_manager.fetch_market_daily_summary(api_key)
    
    if df_market is not None:
        up = len(df_market[df_market['PriceChangePct'] > 0])
        down = len(df_market[df_market['PriceChangePct'] < 0])
        flat = len(df_market) - up - down
        
        c1, c2, c3 = st.columns(3)
        c1.metric("値上がり", f"{up}", delta="Bullish")
        c2.metric("値下がり", f"{down}", delta="-Bearish", delta_color="inverse")
        c3.metric("変わらず", f"{flat}")
    else:
        st.error("本日のデータ取得に失敗しました")

    st.divider()

    # 2. 市場別 売買代金推移 (グラフ分割)
    st.subheader("📊 市場別 売買代金推移 (直近14日)")
    st.caption("※ 売買代金 (単位: 億円)")
    
    df_hist, err_hist = get_market_history(api_key)
    
    if df_hist is not None:
        df_hist = df_hist.set_index('Date')
        
        # 【デバッグ表示】
        # もしカラムが Others しかなかったり、想定と違う名前だった場合のために表示
        # st.write(f"DEBUG: Available Columns: {df_hist.columns.tolist()}")
        
        markets_config = [
            ("Prime", "🟦 プライム市場", "#1976D2"),
            ("Standard", "🟩 スタンダード市場", "#2E7D32"),
            ("Growth", "🟧 グロース市場", "#ED6C02")
        ]
        
        found_data = False
        for mkt_key, mkt_label, mkt_color in markets_config:
            # カラム名に含まれているかチェック (完全一致または部分一致)
            target_col = next((c for c in df_hist.columns if mkt_key in c), None)
            
            if target_col:
                found_data = True
                st.markdown(f"**{mkt_label}**")
                chart_data = df_hist[[target_col]] / 100000000
                st.bar_chart(chart_data, color=mkt_color, height=200)
        
        if not found_data:
            st.warning("指定した市場（Prime/Standard/Growth）のデータが見つかりませんでした。")
            st.write("取得できたデータの内訳:", df_hist.head())
        
    else:
        st.info("履歴データの集計に失敗しました (API制限等の可能性)")
        if err_hist: st.caption(f"Log: {err_hist}")

    st.divider()

    # 3. 売買代金ランキング TOP100
    st.subheader("💰 本日の売買代金ランキング TOP100")
    
    if df_market is not None:
        top100 = df_market.sort_values('TradingValue', ascending=False).head(100).copy()
        
        codes = top100['Code']
        names = top100['CompanyName'] if 'CompanyName' in top100.columns else top100['Code']
        markets = top100['Market'] if 'Market' in top100.columns else '-'
        prices = top100['Close']
        pcts = top100['PriceChangePct']
        vals = top100['TradingValue'] / 100000000
        val_chg = top100['ValChangePct']
        
        disp_df = pd.DataFrame({
            'コード': codes,
            '銘柄名': names,
            '市場': markets,
            '現在値': prices,
            '前日比(%)': pcts,
            '売買代金(億)': vals,
            '代金増減(%)': val_chg
        })
        
        def style_pct(v):
            if pd.isna(v) or v == 0: return ""
            return 'color: #D32F2F; font-weight: bold' if v > 0 else 'color: #1976D2; font-weight: bold'

        st.dataframe(
            disp_df.style.map(style_pct, subset=['前日比(%)', '代金増減(%)']).format({
                '現在値': "¥{:,.0f}", '前日比(%)': "{:+.2f}%", '売買代金(億)': "¥{:,.2f}", '代金増減(%)': "{:+.1f}%"
            }),
            hide_index=True, width='stretch', height=500
        )