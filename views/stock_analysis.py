import streamlit as st
import pandas as pd
import data_manager

def render(api_key):
    st.title("📊 銘柄分析")
    
    # 銘柄リスト取得
    df_list = data_manager.fetch_company_list(api_key)
    options = []
    
    if not df_list.empty:
        # CodeとCompanyNameが確実にある状態で処理
        for index, row in df_list.iterrows():
            code = str(row.get('Code', ''))
            name = str(row.get('CompanyName', ''))
            
            # 5桁コードの末尾0対応
            d_code = code[:-1] if len(code)==5 and code.endswith('0') else code
            options.append(f"{d_code}: {name}")
    else:
        st.warning("銘柄リストの取得に失敗しました。リロードしてください。")
    
    # 検索ボックス
    st.markdown("##### 🔍 銘柄検索")
    selected = st.selectbox("銘柄選択", [""] + options, index=0, label_visibility="collapsed")

    if selected:
        try:
            code_str, name = selected.split(": ", 1)
        except:
            return # 選択フォーマット不正時は何もしない
        
        # データ取得
        df_price, err_p = data_manager.fetch_real_data(code_str, api_key)
        df_fin, err_f = data_manager.fetch_financial_data(code_str, api_key)
        
        st.divider()
        st.markdown(f"### 🏢 {name} <span style='color:gray'>({code_str})</span>", unsafe_allow_html=True)

        # 1. 株価
        if df_price is not None:
            latest = df_price.iloc[-1]
            close = int(latest['Close'])
            val = int(latest.get('TradingValue', 0))
            diff = 0
            diff_pct = 0.0
            
            if len(df_price) >= 2:
                prev = df_price.iloc[-2]
                diff = close - int(prev['Close'])
                if prev.get('TradingValue', 0) > 0:
                    diff_pct = ((val - prev['TradingValue']) / prev['TradingValue']) * 100
            
            c1, c2 = st.columns([1, 1.5])
            c1.metric("終値", f"¥{close:,}", f"{diff:+,} 円")
            
            col = "#D32F2F" if diff_pct >= 0 else "#1976D2"
            arr = "↑" if diff_pct >= 0 else "↓"
            c2.markdown(f"<div style='font-size:1.8em; font-weight:bold'>¥{val:,}</div>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color:{col}'>{arr} 前日比 {diff_pct:+.1f}%</span>", unsafe_allow_html=True)
            
            # 推移
            st.write("###### 📊 直近2週間の推移")
            hist = df_price.tail(14).iloc[::-1].copy()
            hist['DateStr'] = hist['Date'].dt.strftime('%Y-%m-%d')
            hist['Close_Pct'] = hist['Close'].pct_change(-1) * 100
            hist['Val_Pct'] = hist['TradingValue'].pct_change(-1) * 100
            
            disp = pd.DataFrame({
                '日付': hist['DateStr'], '終値': hist['Close'],
                '前日比(%)': hist['Close_Pct'], '売買代金(億)': hist['TradingValue']/100000000,
                '代金比(%)': hist['Val_Pct']
            })
            
            def style_col(v):
                if pd.isna(v) or v==0: return ""
                return 'color: #D32F2F; font-weight: bold' if v>0 else 'color: #1976D2; font-weight: bold'
            
            st.dataframe(
                disp.style.map(style_col, subset=['前日比(%)', '代金比(%)']).format({
                    '終値': "¥{:,.0f}", '前日比(%)': "{:+.2f}%", '売買代金(億)': "¥{:,.2f}", '代金比(%)': "{:+.2f}%"
                }),
                hide_index=True, width='stretch'
            )

        # 2. 財務
        st.divider()
        st.subheader("📋 財務情報 (本決算・過去4年)")
        if df_fin is not None and df_price is not None:
            fin = df_fin.copy()
            fin['PER'] = None
            fin['PBR'] = None
            prices = df_price.set_index('Date')['Close']
            
            for i, r in fin.iterrows():
                try: p = prices.asof(r['開示日'])
                except: p = None
                if pd.notna(p):
                    if r.get('EPS',0) > 0: fin.at[i,'PER'] = p / r['EPS']
                    if r.get('BPS',0) > 0: fin.at[i,'PBR'] = p / r['BPS']
            
            fin['開示日'] = fin['開示日'].dt.strftime('%Y-%m-%d')
            view = fin[['開示日','売上高','営業利益','経常利益','PER','PBR']]
            
            st.dataframe(
                view.style.format({
                    '売上高': "¥{:,.0f}", '営業利益': "¥{:,.0f}", '経常利益': "¥{:,.0f}",
                    'PER': "{:.1f}倍", 'PBR': "{:.2f}倍"
                }, na_rep="-"),
                hide_index=True, width='stretch'
            )
        elif df_fin is not None:
            st.dataframe(df_fin, width='stretch')
        else:
            if err_f: st.warning(f"財務データなし: {err_f}")
            
        # 3. 投資部門別 (個別)
        st.divider()
        st.subheader("🏦 投資家動向 (週次)")
        df_inv, err_i = data_manager.fetch_investor_type_data(code_str, api_key)
        if df_inv is not None:
            # グラフ化
            def get_val(row, keys):
                for k in keys: 
                    if k in row: return float(row[k])
                return 0.0
                
            plot_data = []
            for _, row in df_inv.iterrows():
                d = row.get('Date') or row.get('PublishedDate')
                f_net = get_val(row, ['BrokerageForeignersPurchases', 'ForeignPurchases']) - get_val(row, ['BrokerageForeignersSales', 'ForeignSales'])
                i_net = get_val(row, ['BrokerageIndividualsPurchases', 'IndividualPurchases']) - get_val(row, ['BrokerageIndividualsSales', 'IndividualSales'])
                plot_data.append({'Date':d, '海外(差引)': f_net/100000000, '個人(差引)': i_net/100000000})
            
            df_plot = pd.DataFrame(plot_data).set_index('Date').sort_index()
            st.bar_chart(df_plot, color=["#FF4B4B", "#1f77b4"])
            st.caption("※ 単位: 億円")
        else:
            st.info("この銘柄の投資部門別データはありません")