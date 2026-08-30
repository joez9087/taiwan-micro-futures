import numpy as np
import pandas as pd

def calculate_drawdown_series(equity_series):
    """
    Calculate running underwater drawdown series (in decimals, e.g. -0.15 = -15%).
    """
    running_max = np.maximum.accumulate(equity_series)
    drawdown = (equity_series - running_max) / (running_max + 1e-9)
    return drawdown

def calculate_max_drawdown_duration(drawdown_series):
    """
    Calculate maximum drawdown duration in calendar days (O(N) linear scan).
    """
    if len(drawdown_series) == 0:
        return 0
    is_underwater = drawdown_series < 0
    dates = drawdown_series.index
    
    max_days = 0
    cur_start = None
    
    for i, uw in enumerate(is_underwater):
        if uw:
            if cur_start is None:
                cur_start = dates[i]
            diff_days = (dates[i] - cur_start).days
            if diff_days > max_days:
                max_days = diff_days
        else:
            cur_start = None
            
    return max_days

def calculate_performance_metrics(equity_series, daily_returns, trades_df=None, risk_free_rate=0.015, periods_per_year=250):
    """
    Compute comprehensive quantitative performance metrics.
    """
    if len(equity_series) < 2:
        return {}
        
    init_val = equity_series.iloc[0]
    final_val = equity_series.iloc[-1]
    total_ret = (final_val - init_val) / init_val
    
    total_days = max((equity_series.index[-1] - equity_series.index[0]).days, 1)
    years = total_days / 365.25
    cagr = (final_val / init_val) ** (1.0 / max(years, 0.01)) - 1.0 if final_val > 0 else -1.0
    
    mean_ret = daily_returns.mean() * periods_per_year
    vol = daily_returns.std() * np.sqrt(periods_per_year)
    sharpe = (mean_ret - risk_free_rate) / (vol + 1e-9)
    
    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(periods_per_year)
    sortino = (mean_ret - risk_free_rate) / (downside_vol + 1e-9)
    
    dd_series = calculate_drawdown_series(equity_series)
    mdd = abs(dd_series.min())
    calmar = cagr / (mdd + 1e-9) if mdd > 0 else 0.0
    mdd_duration = calculate_max_drawdown_duration(dd_series)
    
    metrics = {
        "Total Return (%)": round(total_ret * 100.0, 2),
        "CAGR (%)": round(cagr * 100.0, 2),
        "Max Drawdown (%)": round(-mdd * 100.0, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Sortino Ratio": round(sortino, 2),
        "Calmar Ratio": round(calmar, 2),
        "Volatility (Ann. %)": round(vol * 100.0, 2),
        "Max DD Duration (Days)": int(mdd_duration),
        "Total Days": int(total_days)
    }
    
    if trades_df is not None and not trades_df.empty:
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['pnl_twd'] > 0]
        losing_trades = trades_df[trades_df['pnl_twd'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        total_profit = winning_trades['pnl_twd'].sum() if not winning_trades.empty else 0.0
        total_loss = abs(losing_trades['pnl_twd'].sum()) if not losing_trades.empty else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else (999.0 if total_profit > 0 else 0.0)
        
        avg_trade_twd = trades_df['pnl_twd'].mean()
        avg_trade_pts = trades_df['pnl_points'].mean()
        avg_win_twd = winning_trades['pnl_twd'].mean() if not winning_trades.empty else 0.0
        avg_loss_twd = abs(losing_trades['pnl_twd'].mean()) if not losing_trades.empty else 0.0
        win_loss_ratio = avg_win_twd / avg_loss_twd if avg_loss_twd > 0 else 0.0
        
        metrics.update({
            "Total Trades": int(total_trades),
            "Trade Win Rate (%)": round(win_rate * 100.0, 2),
            "Profit Factor": round(profit_factor, 2),
            "Avg PnL per Trade (NT$)": round(avg_trade_twd, 1),
            "Avg PnL per Trade (Points)": round(avg_trade_pts, 1),
            "Win/Loss Ratio": round(win_loss_ratio, 2)
        })
        
    return metrics

def calculate_monthly_returns(daily_returns):
    """
    Construct a Year x Month return matrix (%).
    """
    monthly_ret = daily_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    df_m = pd.DataFrame({
        'Year': monthly_ret.index.year,
        'Month': monthly_ret.index.month,
        'Return': monthly_ret.values * 100.0
    })
    pivot_table = df_m.pivot(index='Year', columns='Month', values='Return')
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pivot_table.columns = [month_names[m - 1] for m in pivot_table.columns]
    
    # Calculate Year-to-Date / Total Annual Return
    yearly_ret = daily_returns.resample('YE').apply(lambda x: (1 + x).prod() - 1) * 100.0
    pivot_table['Annual (%)'] = yearly_ret.values
    return pivot_table
