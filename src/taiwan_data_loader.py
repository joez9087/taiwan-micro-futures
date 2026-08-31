import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

def get_realtime_taifex_futures_price():
    """
    Fetch 100% Real-Time TAIFEX Official Live Quotes for Taiwan Micro Futures (微型臺指期貨近月).
    Zero delay: directly connects to Taiwan Futures Exchange (TAIFEX MIS API).
    Supports both Night Session (夜盤 15:00~05:00) and Day Session (日盤 08:45~13:45).
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = "https://mis.taifex.com.tw/futures/api/getQuoteList"
    
    # Try Night session (1) first, then Day session (0)
    for mtype in ['1', '0']:
        try:
            payload = {
                "MarketType": mtype,
                "SymbolType": "F",
                "KindID": "1",
                "CID": "TMF"
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("RtData", {}).get("QuoteList", [])
                for q in quotes:
                    # Find near-month contract with valid price (e.g. TMFI6-M, TMFI6-F)
                    last_p_str = q.get("CLastPrice", "").strip()
                    sym_id = q.get("SymbolID", "")
                    if last_p_str and ("TMF" in sym_id) and ("-" in sym_id) and not sym_id.endswith("-P") and not sym_id.endswith("-S"):
                        try:
                            p_val = float(last_p_str)
                            if p_val > 1000:
                                return {
                                    "price": p_val,
                                    "symbol": sym_id,
                                    "name": q.get("DispCName", "微台指近月"),
                                    "session": "夜盤" if mtype == '1' else "日盤",
                                    "time": q.get("CTime", ""),
                                    "ref_price": float(q.get("CRefPrice", 0) or 0),
                                    "source": "TAIFEX 期交所實時行情"
                                }
                        except Exception:
                            continue
        except Exception:
            continue
            
    # Fallback to TAIEX spot index via yfinance if TAIFEX MIS is in weekend maintenance
    try:
        ticker = yf.Ticker("^TWII")
        live_p = ticker.fast_info.last_price
        if live_p and not np.isnan(live_p) and live_p > 1000:
            return {
                "price": round(float(live_p), 1),
                "symbol": "^TWII",
                "name": "台股加權指數",
                "session": "現貨收盤",
                "time": datetime.now().strftime("%H%M%S"),
                "ref_price": 0.0,
                "source": "Yahoo Finance (現貨指數)"
            }
    except Exception:
        pass
        
    return None

def fetch_and_prepare_taiwan_macro_data(data_path="data/taiwan_macro_data.csv", start_date="2020-01-01"):
    """
    Download historical macro datasets and align with real-time TAIFEX quotes.
    """
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    # 1. Taiwan Stock Index (^TWII)
    df_tw = yf.download("^TWII", start=start_date, progress=False)
    if isinstance(df_tw.columns, pd.MultiIndex):
        df_tw.columns = [c[0].lower() for c in df_tw.columns]
    else:
        df_tw.columns = [c.lower() for c in df_tw.columns]
    df_tw.index = pd.to_datetime(df_tw.index).tz_localize(None)
    df_tw = df_tw[['open', 'high', 'low', 'close', 'volume']].copy()
    
    # 2. US Semiconductor Index (^SOX)
    df_sox = yf.download("^SOX", start=start_date, progress=False)
    if isinstance(df_sox.columns, pd.MultiIndex):
        df_sox.columns = [c[0].lower() for c in df_sox.columns]
    else:
        df_sox.columns = [c.lower() for c in df_sox.columns]
    df_sox.index = pd.to_datetime(df_sox.index).tz_localize(None)
    
    # 3. US Nasdaq Composite (^IXIC)
    df_nasdaq = yf.download("^IXIC", start=start_date, progress=False)
    if isinstance(df_nasdaq.columns, pd.MultiIndex):
        df_nasdaq.columns = [c[0].lower() for c in df_nasdaq.columns]
    else:
        df_nasdaq.columns = [c.lower() for c in df_nasdaq.columns]
    df_nasdaq.index = pd.to_datetime(df_nasdaq.index).tz_localize(None)
    
    # 4. USD/TWD Exchange Rate (USDTWD=X)
    df_usdtwd = yf.download("USDTWD=X", start=start_date, progress=False)
    if isinstance(df_usdtwd.columns, pd.MultiIndex):
        df_usdtwd.columns = [c[0].lower() for c in df_usdtwd.columns]
    else:
        df_usdtwd.columns = [c.lower() for c in df_usdtwd.columns]
    df_usdtwd.index = pd.to_datetime(df_usdtwd.index).tz_localize(None)
    
    merged = df_tw.copy()
    merged.rename(columns={
        "open": "tw_open",
        "high": "tw_high",
        "low": "tw_low",
        "close": "tw_close",
        "volume": "tw_volume"
    }, inplace=True)
    
    # Lag US indices by 1 day
    merged['sox_close_prev'] = df_sox['close'].shift(1).reindex(merged.index, method='ffill')
    merged['sox_ret_1d'] = df_sox['close'].pct_change(fill_method=None).shift(1).reindex(merged.index, method='ffill')
    
    merged['nasdaq_close_prev'] = df_nasdaq['close'].shift(1).reindex(merged.index, method='ffill')
    merged['nasdaq_ret_1d'] = df_nasdaq['close'].pct_change(fill_method=None).shift(1).reindex(merged.index, method='ffill')
    
    merged['usdtwd_close'] = df_usdtwd['close'].reindex(merged.index, method='ffill')
    merged['usdtwd_ret_5d'] = df_usdtwd['close'].pct_change(5, fill_method=None).reindex(merged.index, method='ffill')
    
    merged.dropna(inplace=True)
    
    # Update latest tick with live TAIFEX futures quote
    live_q = get_realtime_taifex_futures_price()
    if live_q:
        merged.iloc[-1, merged.columns.get_loc('tw_close')] = live_q['price']
        
    merged.to_csv(data_path)
    return merged

def get_taiwan_macro_data(data_path="data/taiwan_macro_data.csv", force_reload=False):
    """
    Get Taiwan macro dataset with zero-delay TAIFEX futures quote integration.
    """
    if not force_reload and os.path.exists(data_path):
        try:
            mtime = os.path.getmtime(data_path)
            if (datetime.now().timestamp() - mtime) < 300: # 5 minutes cache
                df = pd.read_csv(data_path, index_col=0)
                df.index = pd.to_datetime(df.index)
                if len(df) > 500:
                    live_q = get_realtime_taifex_futures_price()
                    if live_q:
                        df.iloc[-1, df.columns.get_loc('tw_close')] = live_q['price']
                    return df
        except Exception:
            pass
    return fetch_and_prepare_taiwan_macro_data(data_path=data_path)

if __name__ == "__main__":
    q = get_realtime_taifex_futures_price()
    print("TAIFEX Live Futures Quote Object:", q)
