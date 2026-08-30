import numpy as np
import pandas as pd
from src.taiwan_data_loader import get_taiwan_macro_data
from src.taiwan_backtester import TaiwanFuturesBacktester

df_raw = get_taiwan_macro_data()

def test_alpha_strategy_v3(
    df_raw,
    macro_ma=60,
    fast_ma=20,
    breakout_n=15,
    exit_n=8,
    atr_mult=2.6,
    breakeven_trigger=1.8, # Move SL to breakeven after price gains 1.8 ATR
    base_lev=1.2,
    boost_lev=1.45
):
    df = df_raw.copy()
    
    # 1. Indicators
    df['tw_ema_fast'] = df['tw_close'].ewm(span=fast_ma, adjust=False).mean()
    df['tw_ema_macro'] = df['tw_close'].ewm(span=macro_ma, adjust=False).mean()
    df['tw_ma_macro'] = df['tw_close'].rolling(macro_ma).mean()
    
    # Donchian
    df['high_chan'] = df['tw_high'].rolling(breakout_n).max().shift(1)
    df['low_chan'] = df['tw_low'].rolling(exit_n).min().shift(1)
    
    # ATR
    tr1 = df['tw_high'] - df['tw_low']
    tr2 = (df['tw_high'] - df['tw_close'].shift(1)).abs()
    tr3 = (df['tw_low'] - df['tw_close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()
    
    # RSI
    delta = df['tw_close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # SOX momentum & TWD
    df['sox_mom3'] = df['sox_ret_1d'].rolling(3).mean()
    df['sox_mom5'] = df['sox_ret_1d'].rolling(5).mean()
    df['twd_risk'] = (df['usdtwd_ret_5d'] > 0.012).astype(int)
    
    df = df.iloc[macro_ma:].copy()
    
    positions = np.zeros(len(df))
    reasons = []
    
    cur_pos = 0.0
    entry_price = 0.0
    highest_p = 0.0
    sl_price = 0.0
    
    closes = df['tw_close'].values
    highs = df['tw_high'].values
    lows = df['tw_low'].values
    ema_macros = df['tw_ema_macro'].values
    ema_fasts = df['tw_ema_fast'].values
    high_chans = df['high_chan'].values
    low_chans = df['low_chan'].values
    atrs = df['atr_14'].values
    rsis = df['rsi_14'].values
    sox_rets = df['sox_ret_1d'].values
    sox_moms = df['sox_mom3'].values
    twd_risks = df['twd_risk'].values
    
    for i in range(len(df)):
        c = closes[i]
        h = highs[i]
        l = lows[i]
        e_macro = ema_macros[i]
        e_fast = ema_fasts[i]
        h_chan = high_chans[i]
        l_chan = low_chans[i]
        atr = atrs[i]
        rsi = rsis[i]
        sox_r = sox_rets[i]
        sox_m = sox_moms[i]
        twd_r = twd_risks[i]
        
        reason = "HOLD / CASH"
        
        # Bull Regime: Price > 60 EMA and 20 EMA >= 60 EMA (or price above 60 MA)
        if c > e_macro:
            if cur_pos == 0.0:
                # Entry 1: Breakout with SOX momentum
                if (c > h_chan or (c > e_fast and sox_r > 0.005)) and twd_r == 0 and rsi < 78:
                    cur_pos = boost_lev if (sox_m > 0 and c > e_fast) else base_lev
                    entry_price = c
                    highest_p = h
                    sl_price = c - atr_mult * atr
                    reason = "BULL_BREAKOUT_SOX_ENTRY"
                # Entry 2: Pullback Dip Buy
                elif c > e_fast and rsi > 38 and rsi < 58 and sox_r > 0 and twd_r == 0:
                    cur_pos = base_lev
                    entry_price = c
                    highest_p = h
                    sl_price = c - atr_mult * atr
                    reason = "BULL_PULLBACK_DIP_BUY"
            else:
                # Update highest price and trailing stop
                if h > highest_p:
                    highest_p = h
                
                # Check Breakeven ratchet
                if (highest_p - entry_price) > breakeven_trigger * atr:
                    # SL is at least at entry price (breakeven)
                    sl_price = max(sl_price, entry_price + 0.2 * atr)
                    
                # Trailing stop ratchet
                new_trailing = highest_p - atr_mult * atr
                if new_trailing > sl_price:
                    sl_price = new_trailing
                    
                # Exit logic
                if c < sl_price or c < e_macro:
                    cur_pos = 0.0
                    reason = "BULL_TRAILING_STOP_EXIT"
                elif cur_pos < boost_lev and sox_m > 0.005 and c > e_fast and rsi < 75:
                    cur_pos = boost_lev
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

print("--- Testing Strategy V3 Parameter Grid ---")
for mult in [2.2, 2.5, 2.8, 3.0, 3.2]:
    for be in [1.5, 1.8, 2.0, 2.5]:
        for base in [1.1, 1.2, 1.25]:
            for boost in [1.35, 1.45, 1.55]:
                sig_df = test_alpha_strategy_v3(df_raw, atr_mult=mult, breakeven_trigger=be, base_lev=base, boost_lev=boost)
                res = TaiwanFuturesBacktester(initial_capital=200000.0).run(sig_df)
                sm = res['strategy_metrics']
                bm = res['benchmark_metrics']
                if sm['Sharpe Ratio'] >= 1.28 and sm['Total Return (%)'] > 400.0 and abs(sm['Max Drawdown (%)']) < 25.0:
                    print(f"mult={mult:<3} be={be:<3} base={base:<4} boost={boost:<4} | Ret: {sm['Total Return (%)']:>6.1f}% | MDD: {sm['Max Drawdown (%)']:>6.1f}% | Sharpe: {sm['Sharpe Ratio']:>4.2f} | Sortino: {sm['Sortino Ratio']:>4.2f} | Calmar: {sm['Calmar Ratio']:>4.2f} | WinRate: {sm['Trade Win Rate (%)']:>4.1f}% | Trades: {sm['Total Trades']}", flush=True)

print(f"Benchmark: Ret: {bm['Total Return (%)']:.1f}% | MDD: {bm['Max Drawdown (%)']:.1f}% | Sharpe: {bm['Sharpe Ratio']:.2f}")
