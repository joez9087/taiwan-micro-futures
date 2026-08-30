import numpy as np
import pandas as pd
from src.taiwan_data_loader import get_taiwan_macro_data
from src.taiwan_backtester import TaiwanFuturesBacktester

df_raw = get_taiwan_macro_data()

def test_asymmetric_alpha(
    df_raw,
    macro_ma=60,
    fast_ma=20,
    breakout_n=20,
    trail_atr_mult=2.2,
    tight_atr_mult=1.6,
    profit_trigger=3.0,
    bull_lev=1.35
):
    df = df_raw.copy()
    
    df['tw_ema_fast'] = df['tw_close'].ewm(span=fast_ma, adjust=False).mean()
    df['tw_ema_macro'] = df['tw_close'].ewm(span=macro_ma, adjust=False).mean()
    df['high_chan'] = df['tw_high'].rolling(breakout_n).max().shift(1)
    df['low_chan'] = df['tw_low'].rolling(10).min().shift(1)
    
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
    
    df = df.iloc[macro_ma:].copy()
    
    positions = np.zeros(len(df))
    reasons = []
    
    cur_pos = 0.0
    entry_p = 0.0
    highest_p = 0.0
    sl_p = 0.0
    
    closes = df['tw_close'].values
    highs = df['tw_high'].values
    lows = df['tw_low'].values
    e_macros = df['tw_ema_macro'].values
    e_fasts = df['tw_ema_fast'].values
    h_chans = df['high_chan'].values
    sox_rs = df['sox_ret_1d'].values
    sox_ms = df['sox_mom3'].values
    twd_rs = df['twd_risk'].values
    rsis = df['rsi_14'].values
    atrs = df['atr_14'].values
    
    for i in range(len(df)):
        c = closes[i]
        h = highs[i]
        e_macro = e_macros[i]
        e_fast = e_fasts[i]
        h_chan = h_chans[i]
        sox_r = sox_rs[i]
        sox_m = sox_ms[i]
        twd_r = twd_rs[i]
        rsi = rsis[i]
        a = atrs[i]
        
        reason = "HOLD / CASH"
        
        # Bull Regime: Price > 60 EMA and 20 EMA > 60 EMA (or price above 60 EMA with positive slope)
        if c > e_macro and e_fast >= e_macro * 0.995:
            if cur_pos == 0.0:
                # Entry A: Breakout with SOX momentum
                if (c >= h_chan or (c > e_fast and sox_r > 0.003 and sox_m > 0)) and twd_r == 0 and rsi < 75:
                    cur_pos = bull_lev if (sox_m > 0.005 and c > e_fast) else 1.15
                    entry_p = c
                    highest_p = h
                    sl_p = c - 2.0 * a
                    reason = "BULL_ENTRY_BREAKOUT"
                # Entry B: Pullback Dip
                elif c > e_fast and rsi > 40 and rsi < 58 and sox_r > 0 and twd_r == 0:
                    cur_pos = 1.15
                    entry_p = c
                    highest_p = h
                    sl_p = c - 2.0 * a
                    reason = "BULL_ENTRY_DIP"
            else:
                if h > highest_p:
                    highest_p = h
                
                # Check profit target threshold
                profit_atr = (highest_p - entry_p) / (a + 1e-9)
                if profit_atr >= profit_trigger:
                    curr_trail_mult = tight_atr_mult
                else:
                    curr_trail_mult = trail_atr_mult
                    
                dynamic_stop = highest_p - curr_trail_mult * a
                if dynamic_stop > sl_p:
                    sl_p = dynamic_stop
                    
                if c < sl_p or c < e_macro:
                    cur_pos = 0.0
                    reason = "BULL_EXIT_STOP"
                elif cur_pos < bull_lev and sox_m > 0.005 and c > e_fast and rsi < 72:
                    cur_pos = bull_lev
                    reason = "BULL_SCALE_UP"
        else:
            if cur_pos > 0.0:
                cur_pos = 0.0
                reason = "BEAR_REGIME_SAFETY_EXIT"
            else:
                cur_pos = 0.0
                reason = "BEAR_REGIME_CASH_DEFENSE"
                
        positions[i] = cur_pos
        reasons.append(reason)
        
    df['target_position'] = positions
    df['trade_position'] = df['target_position'].shift(1).fillna(0.0)
    df['signal_reason'] = reasons
    return df

print("--- Testing Asymmetric Alpha Strategy ---", flush=True)
for p_trig in [2.5, 3.0, 3.5]:
    for tr_m in [2.2, 2.5, 2.8]:
        for ti_m in [1.5, 1.8, 2.0]:
            for b_lev in [1.3, 1.4, 1.5]:
                sig_df = test_asymmetric_alpha(df_raw, trail_atr_mult=tr_m, tight_atr_mult=ti_m, profit_trigger=p_trig, bull_lev=b_lev)
                res = TaiwanFuturesBacktester(initial_capital=200000.0).run(sig_df)
                sm = res['strategy_metrics']
                bm = res['benchmark_metrics']
                if sm['Sharpe Ratio'] >= 1.22 and sm['Total Return (%)'] > 300.0 and abs(sm['Max Drawdown (%)']) < 22.0:
                    print(f"p_trig={p_trig} tr_m={tr_m} ti_m={ti_m} b_lev={b_lev} | Ret: {sm['Total Return (%)']:>6.1f}% | MDD: {sm['Max Drawdown (%)']:>6.1f}% | Sharpe: {sm['Sharpe Ratio']:>4.2f} | Calmar: {sm['Calmar Ratio']:>4.2f} | WinRate: {sm['Trade Win Rate (%)']:>4.1f}% | Trades: {sm['Total Trades']}", flush=True)

print(f"Benchmark: Ret: {bm['Total Return (%)']:.1f}% | MDD: {bm['Max Drawdown (%)']:.1f}% | Sharpe: {bm['Sharpe Ratio']:.2f}")
