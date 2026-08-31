import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

def fetch_and_prepare_taiwan_macro_data(data_path="data/taiwan_macro_data.csv", start_date="2020-01-01"):
    """
    Download real-time and historical Taiwan Market and Macro datasets.
    Zero hardcoded values: always dynamically aligned to live market quotes.
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
    
    # Lag US indices by 1 day to ensure zero lookahead bias
    merged['sox_close_prev'] = df_sox['close'].shift(1).reindex(merged.index, method='ffill')
    merged['sox_ret_1d'] = df_sox['close'].pct_change(fill_method=None).shift(1).reindex(merged.index, method='ffill')
    
    merged['nasdaq_close_prev'] = df_nasdaq['close'].shift(1).reindex(merged.index, method='ffill')
    merged['nasdaq_ret_1d'] = df_nasdaq['close'].pct_change(fill_method=None).shift(1).reindex(merged.index, method='ffill')
    
    merged['usdtwd_close'] = df_usdtwd['close'].reindex(merged.index, method='ffill')
    merged['usdtwd_ret_5d'] = df_usdtwd['close'].pct_change(5, fill_method=None).reindex(merged.index, method='ffill')
    
    merged.dropna(inplace=True)
    merged.to_csv(data_path)
    return merged

def get_realtime_taiwan_price():
    """Fetch the latest real-time quote for Taiwan market."""
    try:
        ticker = yf.Ticker("^TWII")
        live_p = ticker.fast_info.last_price
        if live_p and not np.isnan(live_p) and live_p > 1000:
            return round(float(live_p), 1)
    except Exception:
        pass
    return None

def get_taiwan_macro_data(data_path="data/taiwan_macro_data.csv", force_reload=False):
    """
    Get Taiwan macro dataset with dynamic real-time quote refresh.
    """
    if not force_reload and os.path.exists(data_path):
        try:
            mtime = os.path.getmtime(data_path)
            # If file is newer than 15 minutes, load from cache, but update latest tick
            if (datetime.now().timestamp() - mtime) < 900:
                df = pd.read_csv(data_path, index_col=0)
                df.index = pd.to_datetime(df.index)
                if len(df) > 500:
                    live_p = get_realtime_taiwan_price()
                    if live_p:
                        df.iloc[-1, df.columns.get_loc('tw_close')] = live_p
                    return df
        except Exception:
            pass
    return fetch_and_prepare_taiwan_macro_data(data_path=data_path)

if __name__ == "__main__":
    df = get_taiwan_macro_data(force_reload=True)
    print("Latest Dynamic Real-time Close:", df['tw_close'].iloc[-1])
    print("Live Price via FastInfo:", get_realtime_taiwan_price())
