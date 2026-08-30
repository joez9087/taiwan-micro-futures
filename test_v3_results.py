import numpy as np
import pandas as pd
from src.taiwan_data_loader import get_taiwan_macro_data
from src.taiwan_backtester import TaiwanFuturesBacktester

df_raw = get_taiwan_macro_data()

def test_long_short_strategy(
    df_raw,
    macro_ma=60,
    fast_ma=20,
    breakout_n=15,
    exit_n=10,
    bull_lev=1.35,
    short_lev=0.6
):
    df = df_raw.copy()
    
    df['tw_ema_fast'] = df['tw_close'].ewm(span=fast_ma, adjust=False).mean()
    df['tw_ema_macro'] = df['tw_close'].ewm(span=macro_ma, adjust=False).mean()
    df['high_chan'] = df['tw_high'].rolling(breakout_n).max().shift(1)
    df['low_chan'] = df['tw_low'].rolling(exit_n).min().shift(1)
    
    tr1 = df['tw_high'] - df['tw_low']
    tr2 = (df['tw_high'] - df['tw_close'].shift(1)).abs()
    tr3 = (df['tw_low'] - df['tw_close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    delta = df['tw_close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    df['sox_mom3'] = df['sox_ret_1d'].rolling(3).mean()
    df['twd_risk'] = (df['usdtwd_ret_5d'] > 0.015).astype(int)
    
    # Supertrend
    high = df['tw_high'].values
    low = df['tw_low'].values
    close = df['tw_close'].values
    atr = df['atr_14'].values
    n = len(df)
    
    hl2 = (high + low) / 2.0
    upperband = hl2 + 2.5 * atr
    lowerband = hl2 - 2.5 * atr
    trend = np.ones(n)
    upper_f = upperband.copy()
    lower_f = lowerband.copy()
    
    for i in range(1, n):
        if np.isnan(atr[i]):
            continue
        if upperband[i] < upper_f[i-1] or close[i-1] > upper_f[i-1]:
            upper_f[i] = upperband[i]
        else:
            upper_f[i] = upper_f[i-1]
            
        if lowerband[i] > lower_f[i-1] or close[i-1] < lower_f[i-1]:
            lower_f[i] = lowerband[i]
        else:
            lower_f[i] = lower_f[i-1]
            
        if close[i] > upper_f[i-1]:
            trend[i] = 1
        elif close[i] < lower_f[i-1]:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]
            
    df['supertrend'] = trend
    df = df.iloc[macro_ma:].copy()
    
    positions = np.zeros(len(df))
    reasons = []
    
    cur_pos = 0.0
    
    closes = df['tw_close'].values
    highs = df['tw_high'].values
    lows = df['tw_low'].values
    e_macros = df['tw_ema_macro'].values
    e_fasts = df['tw_ema_fast'].values
    h_chans = df['high_chan'].values
    l_chans = df['low_chan'].values
    sts = df['supertrend'].values
    sox_rs = df['sox_ret_1d'].values
    sox_ms = df['sox_mom3'].values
    twd_rs = df['twd_risk'].values
    rsis = df['rsi_14'].values
    
    for i in range(len(df)):
        c = closes[i]
        e_macro = e_macros[i]
        e_fast = e_fasts[i]
        h_chan = h_chans[i]
        l_chan = l_chans[i]
        st = sts[i]
        sox_r = sox_rs[i]
        sox_m = sox_ms[i]
        twd_r = twd_rs[i]
        rsi = rsis[i]
        
        reason = "HOLD / CASH"
        
        # Bull Market Regime
        if c > e_macro:
            if (c > h_chan or (st == 1 and sox_r > 0.002)) and twd_r == 0:
                cur_pos = bull_lev if (sox_m > 0 and c > e_fast) else 1.15
                reason = "BULL_LONG_BREAKOUT"
            elif cur_pos == 0 and (rsi > 36 and rsi < 58) and st == 1:
                cur_pos = 1.10
                reason = "BULL_LONG_DIP"
            elif cur_pos > 0 and (c < e_macro or (st == -1 and c < e_fast and c < l_chan)):
                cur_pos = 0.0
                reason = "BULL_EXIT"
                
        # Bear Market Regime
        else:
            if short_lev > 0:
                # Bear short entry
                if c < l_chan and st == -1 and sox_m < 0 and rsi < 48:
                    cur_pos = -short_lev
                    reason = "BEAR_SHORT_BREAKDOWN"
                elif cur_pos < 0 and (st == 1 or c > e_fast or rsi < 25):
                    cur_pos = 0.0
                    reason = "BEAR_SHORT_COVER"
                elif cur_pos > 0:
                    cur_pos = 0.0
                    reason = "BEAR_SAFETY_EXIT"
            else:
                if cur_pos > 0:
                    cur_pos = 0.0
                    reason = "BEAR_SAFETY_EXIT"
                else:
                    cur_pos = 0.0
                    reason = "BEAR_CASH_DEFENSE"
                    
        positions[i] = cur_pos
        reasons.append(reason)
        
    df['target_position'] = positions
    df['trade_position'] = df['target_position'].shift(1).fillna(0.0)
    df['signal_reason'] = reasons
    return df

print("--- Testing Long & Short Strategy ---", flush=True)
for s_lev in [0.0, 0.3, 0.5, 0.6, 0.75, 0.9]:
    for b_lev in [1.35, 1.45, 1.55, 1.65]:
        sig_df = test_long_short_strategy(df_raw, bull_lev=b_lev, short_lev=s_lev)
        res = TaiwanFuturesBacktester(initial_capital=200000.0).run(sig_df)
        sm = res['strategy_metrics']
        bm = res['benchmark_metrics']
        print(f"short_lev={s_lev:<4} bull_lev={b_lev:<4} | Ret: {sm['Total Return (%)']:>6.1f}% | MDD: {sm['Max Drawdown (%)']:>6.1f}% | Sharpe: {sm['Sharpe Ratio']:>4.2f} | Sortino: {sm['Sortino Ratio']:>4.2f} | Trades: {sm['Total Trades']}", flush=True)

print(f"Benchmark: Ret: {bm['Total Return (%)']:.1f}% | MDD: {bm['Max Drawdown (%)']:.1f}% | Sharpe: {bm['Sharpe Ratio']:.2f}", flush=True)
