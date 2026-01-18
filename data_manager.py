import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# --- V2 API設定 ---
BASE_URL_V2 = "https://api.jquants.com/v2"

def _log(label, msg):
    """共通デバッグログ"""
    print(f"[{label}] {msg}")

def fetch_company_list(api_key):
    """
    銘柄一覧取得 (市場区分 Market を含む)
    """
    url = f"{BASE_URL_V2}/equities/master"
    headers = {"x-api-key": api_key.strip()}
    
    _log("List", "Fetching company list...")
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            res_json = response.json()
            info = res_json.get("equities", []) or res_json.get("info", []) or res_json.get("data", [])
            
            if len(info) > 0:
                df = pd.DataFrame(info)
                rename_map = {
                    'Code': 'Code', 'Name': 'CompanyName', 'CoName': 'CompanyName', 'CompanyName': 'CompanyName',
                    'S33': 'SectorCode', 'S33Nm': 'SectorName',
                    'MktNm': 'Market', 'Market': 'Market'
                }
                curr_cols = df.columns
                final_rename = {k:v for k,v in rename_map.items() if k in curr_cols}
                df = df.rename(columns=final_rename)
                
                if 'CompanyName' not in df.columns: df['CompanyName'] = df['Code']
                if 'Market' not in df.columns: df['Market'] = 'Others'
                
                # Codeを文字列に統一
                df['Code'] = df['Code'].astype(str)
                
                # 【デバッグ】市場区分のユニークな値を確認
                unique_markets = df['Market'].unique()
                _log("List", f"Market categories found: {unique_markets}")
                _log("List", f"Sample Codes: {df['Code'].head(3).tolist()}")
                
                return df
            else:
                _log("List", "Response empty")
        else:
            _log("List", f"Status Code: {response.status_code}")
    except Exception as e:
        _log("List", f"Error: {e}")
        pass
    return pd.DataFrame()

def fetch_real_data(code, api_key):
    """個別株価取得"""
    target_code = str(code) + "0" if len(str(code)) == 4 else str(code)
    now = datetime.now()
    end_date = now.strftime("%Y%m%d")
    start_date = (now - timedelta(days=365 * 4 + 60)).strftime("%Y%m%d")
    
    url = f"{BASE_URL_V2}/equities/bars/daily?code={target_code}&from={start_date}&to={end_date}"
    headers = {"x-api-key": api_key.strip()}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            res_json = response.json()
            quotes = res_json.get("daily_quotes", []) or res_json.get("data", [])
            if len(quotes) > 0:
                df = pd.DataFrame(quotes)
                rename_map = {'C': 'Close', 'O': 'Open', 'H': 'High', 'L': 'Low', 'Vo': 'Volume', 'Va': 'TradingValue', 'Date': 'Date'}
                df = df.rename(columns=rename_map)
                df = df.sort_values('Date')
                df['Date'] = pd.to_datetime(df['Date'])
                return df, None
        return None, "データなし"
    except Exception as e:
        return None, str(e)

def fetch_financial_data(code, api_key):
    """財務情報取得"""
    target_code = str(code) + "0" if len(str(code)) == 4 else str(code)
    now = datetime.now()
    end_date = now.strftime("%Y%m%d")
    start_date = (now - timedelta(days=365 * 4)).strftime("%Y%m%d")
    
    url = f"{BASE_URL_V2}/fins/summary?code={target_code}&from={start_date}&to={end_date}"
    headers = {"x-api-key": api_key.strip()}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            res_json = response.json()
            statements = res_json.get("info", []) or res_json.get("statements", []) or res_json.get("data", [])
            
            if len(statements) > 0:
                df = pd.DataFrame(statements)
                target_cols = {'DiscDate': '開示日', 'CurFYEn': '決算期末', 'DocType': '種別コード', 'Sales': '売上高', 'OP': '営業利益', 'OdP': '経常利益', 'EPS': 'EPS', 'BPS': 'BPS'}
                backup_cols = {'DisclosedDate': '開示日', 'CurrentFiscalYearEndDate': '決算期末', 'TypeOfDocument': '種別コード', 'NetSales': '売上高', 'OperatingProfit': '営業利益', 'OrdinaryProfit': '経常利益', 'EarningsPerShare': 'EPS', 'BookValuePerShare': 'BPS'}
                
                combined_map = {**target_cols, **backup_cols}
                existing_map = {k:v for k,v in combined_map.items() if k in df.columns}
                if not existing_map: return None, "カラム形式不明"
                df = df.rename(columns=existing_map)
                
                for c in ['売上高', '営業利益', '経常利益', 'EPS', 'BPS']:
                    if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                
                if '種別コード' in df.columns:
                    df = df[~df['種別コード'].astype(str).str.contains("Forecast", case=False, na=False)]
                    df = df[df['種別コード'].astype(str).str.contains("FY|4Q", case=False, na=False)]
                
                if '開示日' in df.columns:
                    df['開示日'] = pd.to_datetime(df['開示日'])
                    if '決算期末' in df.columns:
                        df = df.sort_values('開示日', ascending=False).drop_duplicates(subset=['決算期末'], keep='first')
                return df, None
            return None, "データなし"
        return None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, str(e)

def fetch_market_daily_summary(api_key):
    """【市場分析】最新日と前日の2日分を取得"""
    headers = {"x-api-key": api_key.strip()}
    valid_dfs = []
    
    # 過去10日走査して2営業日分探す
    for i in range(10):
        target_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"{BASE_URL_V2}/equities/bars/daily?date={target_date}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                quotes = response.json().get("daily_quotes", []) or response.json().get("data", [])
                if len(quotes) > 100:
                    df = pd.DataFrame(quotes)
                    df = df.rename(columns={'Code': 'Code', 'C': 'Close', 'O': 'Open', 'Va': 'TradingValue'})
                    df['Code'] = df['Code'].astype(str)
                    for c in ['Close', 'TradingValue']: df[c] = pd.to_numeric(df[c], errors='coerce')
                    valid_dfs.append(df[['Code', 'Close', 'TradingValue']])
                    if len(valid_dfs) == 2: break
        except: continue
    
    if len(valid_dfs) == 0: return None, "市場データなし"
    
    df_latest = valid_dfs[0]
    if len(valid_dfs) >= 2:
        df_prev = valid_dfs[1]
        merged = pd.merge(df_latest, df_prev, on='Code', how='left', suffixes=('', '_prev'))
        merged['PriceChangePct'] = ((merged['Close'] - merged['Close_prev']) / merged['Close_prev']) * 100
        merged['ValChangePct'] = ((merged['TradingValue'] - merged['TradingValue_prev']) / merged['TradingValue_prev']) * 100
        final_df = merged
    else:
        final_df = df_latest
        final_df['PriceChangePct'] = 0.0
        final_df['ValChangePct'] = 0.0

    df_list = fetch_company_list(api_key)
    if not df_list.empty:
        df_list['Code'] = df_list['Code'].astype(str)
        final_df = pd.merge(final_df, df_list, on='Code', how='left')
        final_df['CompanyName'] = final_df['CompanyName'].fillna(final_df['Code'])
        final_df['Market'] = final_df['Market'].fillna('-')
    else:
        final_df['CompanyName'] = final_df['Code']
        final_df['Market'] = '-'
        final_df['SectorName'] = '-'

    return final_df, None

def fetch_market_history(api_key, days=14):
    """
    【修正版】市場別売買代金推移を集計 (デバッグログ付き)
    """
    headers = {"x-api-key": api_key.strip()}
    
    _log("Hist", "Starting market history fetch...")
    
    # 1. 銘柄リスト取得
    df_list = fetch_company_list(api_key)
    if df_list.empty: return None, "銘柄リスト取得失敗"
    
    # 【重要】市場名の正規化ヘルパー
    def normalize_market(m):
        m = str(m)
        if "Prime" in m or "プライム" in m: return "Prime"
        if "Standard" in m or "スタンダード" in m: return "Standard"
        if "Growth" in m or "グロース" in m: return "Growth"
        return "Others"
    
    # マッピング辞書作成
    df_list['NormMarket'] = df_list['Market'].apply(normalize_market)
    
    # 【デバッグ】コードと正規化市場のサンプル確認
    _log("Hist", "Mapping Sample (Code -> NormMarket):")
    _log("Hist", df_list[['Code', 'NormMarket']].head(3).to_dict('records'))
    
    market_map = df_list.set_index('Code')['NormMarket'].to_dict()
    
    daily_data = []
    
    # 2. 過去N日分の日付を走査
    for i in range(days):
        target_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"{BASE_URL_V2}/equities/bars/daily?date={target_date}"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                quotes = response.json().get("daily_quotes", []) or response.json().get("data", [])
                
                if len(quotes) > 100:
                    df = pd.DataFrame(quotes)
                    df = df.rename(columns={'Code': 'Code', 'Va': 'TradingValue'})
                    df['Code'] = df['Code'].astype(str)
                    df['TradingValue'] = pd.to_numeric(df['TradingValue'], errors='coerce').fillna(0)
                    
                    # 【デバッグ】取得データのCodeサンプル
                    if i == 0: # 初回のみ
                        _log("Hist", f"Quotes Codes Sample: {df['Code'].head(3).tolist()}")
                    
                    # 市場区分をマッピング
                    df['Market'] = df['Code'].map(market_map).fillna('Others')
                    
                    # 【デバッグ】マッピング後の市場別カウント
                    if i == 0:
                        _log("Hist", f"Market Counts on {target_date}: {df['Market'].value_counts().to_dict()}")
                    
                    # 市場ごとの合計を計算
                    daily_sum = df.groupby('Market')['TradingValue'].sum()
                    
                    row = daily_sum.to_dict()
                    row['Date'] = target_date
                    daily_data.append(row)
                else:
                    _log("Hist", f"Skip {target_date}: Too few records ({len(quotes)})")
            else:
                _log("Hist", f"Skip {target_date}: API Status {response.status_code}")
                
        except Exception as e:
            _log("Hist", f"Error {target_date}: {e}")
            continue
            
    if not daily_data:
        return None, "履歴データが取得できませんでした (全日程で失敗)"
        
    df_hist = pd.DataFrame(daily_data)
    df_hist['Date'] = pd.to_datetime(df_hist['Date'])
    df_hist = df_hist.sort_values('Date')
    
    return df_hist, None

def fetch_investor_type_data(code, api_key):
    """個別銘柄用 投資部門別データ"""
    if not code: code = "TSEPrime"
    target_code = str(code)
    now = datetime.now()
    end_date = now.strftime("%Y%m%d")
    start_date = (now - timedelta(days=365)).strftime("%Y%m%d")
    
    url = f"{BASE_URL_V2}/equities/investor-types?code={target_code}&from={start_date}&to={end_date}"
    headers = {"x-api-key": api_key.strip()}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("investor_types", []) or response.json().get("data", [])
            if len(data) > 0: return pd.DataFrame(data), None
            return None, "データなし"
        else:
            return None, f"API Error {response.status_code}"
    except Exception as e:
        return None, str(e)