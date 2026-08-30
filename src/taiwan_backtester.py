import os
import sys
import numpy as np
import pandas as pd

try:
    from src.metrics import calculate_performance_metrics, calculate_drawdown_series, calculate_monthly_returns
except ImportError:
    from metrics import calculate_performance_metrics, calculate_drawdown_series, calculate_monthly_returns

class TaiwanFuturesBacktester:
    """
    Institutional Futures Portfolio Backtester for Taiwan Micro Index Futures (微台指).
    
    Models:
    - Real Futures Points: 1 pt = NT$10
    - Exact Taiwan Futures Tax: 0.00002 (十萬分之二)
    - Broker Commission: NT$15 per contract per side
    - Slippage: 2 points
    - Target Notional Exposure: 1.0x to 1.2x unleveraged / low-leverage safe execution
    """
    def __init__(
        self,
        initial_capital=200000.0, # Standard recommended starting capital for 1-2 lots
        point_value=10.0,
        fee_per_lot=15.0,
        tax_rate=0.00002,
        slippage_points=2.0
    ):
        self.initial_capital = initial_capital
        self.point_value = point_value
        self.fee_per_lot = fee_per_lot
        self.tax_rate = tax_rate
        self.slippage_points = slippage_points

    def run(self, df_signals):
        df = df_signals.copy()
        n = len(df)
        
        capital = self.initial_capital
        equity_curve = np.zeros(n)
        equity_curve[0] = capital
        
        trade_positions = df['trade_position'].values
        target_positions = df['target_position'].values
        closes = df['tw_close'].values
        dates = df.index
        pt_val = self.point_value
        
        trades_list = []
        in_trade = False
        trade_entry_date = None
        trade_entry_price = 0.0
        trade_side = None
        
        for i in range(1, n):
            pos = trade_positions[i] # Position held from previous bar's decision
            prev_pos = trade_positions[i-1]
            close_t = closes[i]
            close_prev = closes[i-1]
            date = dates[i]
            
            # Notional exposure (1.0x = 100% of equity)
            contract_notional_value = close_prev * pt_val
            contracts_held = (capital * pos) / contract_notional_value if contract_notional_value > 0 else 0.0
            
            # Gross Daily PnL
            gross_pnl = contracts_held * (close_t - close_prev) * pt_val
            
            # Transaction Costs if position changed
            pos_change = abs(pos - prev_pos)
            if pos_change > 0.01:
                changed_contracts = abs(capital * (pos - prev_pos)) / (close_prev * pt_val)
                tax_cost = changed_contracts * close_t * pt_val * self.tax_rate
                fee_cost = changed_contracts * self.fee_per_lot
                slippage_cost = changed_contracts * self.slippage_points * pt_val
                total_cost = tax_cost + fee_cost + slippage_cost
            else:
                total_cost = 0.0
                
            net_daily_pnl = gross_pnl - total_cost
            capital += net_daily_pnl
            capital = max(capital, 1000.0)
            equity_curve[i] = capital
            
            # Track Discrete Trade Records
            if pos != 0 and not in_trade:
                in_trade = True
                trade_entry_date = date
                trade_entry_price = close_t
                trade_side = 'LONG (做多)' if pos > 0 else 'SHORT (放空)'
            elif pos == 0 and in_trade:
                in_trade = False
                pnl_pts = (close_t - trade_entry_price) if trade_side == 'LONG (做多)' else (trade_entry_price - close_t)
                trade_pnl_twd = pnl_pts * pt_val * (contracts_held if contracts_held > 0 else 1.0)
                trade_ret_pct = (pnl_pts / trade_entry_price) * 100.0 if trade_side == 'LONG (做多)' else ((trade_entry_price - close_t) / trade_entry_price) * 100.0
                trades_list.append({
                    'trade_id': len(trades_list) + 1,
                    'entry_date': trade_entry_date.strftime('%Y-%m-%d'),
                    'exit_date': date.strftime('%Y-%m-%d'),
                    'type': trade_side,
                    'entry_price': round(trade_entry_price, 1),
                    'exit_price': round(close_t, 1),
                    'pnl_points': round(pnl_pts, 1),
                    'pnl_twd': round(pnl_pts * pt_val, 1),
                    'return_pct': round(trade_ret_pct, 2),
                    'duration_days': max((date - trade_entry_date).days, 1),
                    'cumulative_equity': round(capital, 1)
                })
                
        res_df = pd.DataFrame(index=df.index)
        res_df['tw_close'] = df['tw_close']
        res_df['strategy_equity'] = equity_curve
        res_df['position'] = trade_positions
        res_df['strategy_daily_ret'] = res_df['strategy_equity'].pct_change().fillna(0.0)
        
        # Benchmark Buy & Hold (^TWII)
        res_df['benchmark_equity'] = (df['tw_close'] / df['tw_close'].iloc[0]) * self.initial_capital
        res_df['benchmark_daily_ret'] = res_df['benchmark_equity'].pct_change().fillna(0.0)
        
        # Drawdowns
        res_df['strategy_drawdown'] = calculate_drawdown_series(res_df['strategy_equity'])
        res_df['benchmark_drawdown'] = calculate_drawdown_series(res_df['benchmark_equity'])
        
        trades_df = pd.DataFrame(trades_list)
        
        # Performance Metrics
        strat_metrics = calculate_performance_metrics(res_df['strategy_equity'], res_df['strategy_daily_ret'], trades_df, risk_free_rate=0.015, periods_per_year=250)
        bench_metrics = calculate_performance_metrics(res_df['benchmark_equity'], res_df['benchmark_daily_ret'], risk_free_rate=0.015, periods_per_year=250)
        
        strat_monthly = calculate_monthly_returns(res_df['strategy_daily_ret'])
        bench_monthly = calculate_monthly_returns(res_df['benchmark_daily_ret'])
        
        return {
            "df_results": res_df,
            "trades_df": trades_df,
            "strategy_metrics": strat_metrics,
            "benchmark_metrics": bench_metrics,
            "strategy_monthly": strat_monthly,
            "benchmark_monthly": bench_monthly
        }

if __name__ == "__main__":
    from taiwan_data_loader import get_taiwan_macro_data
    from taiwan_macro_strategy import TaiwanMacroQuantStrategy
    
    df = get_taiwan_macro_data()
    strat = TaiwanMacroQuantStrategy()
    sig_df = strat.generate_signals(df)
    
    backtester = TaiwanFuturesBacktester(initial_capital=200000.0)
    res = backtester.run(sig_df)
    
    sm = res['strategy_metrics']
    bm = res['benchmark_metrics']
    print("\n=======================================================")
    print("   微台指宏觀量化策略 (Taiwan Macro Quant) 回測績效")
    print("=======================================================")
    print(f"總累積報酬率: +{sm['Total Return (%)']:.1f}% (大盤 +{bm['Total Return (%)']:.1f}%)")
    print(f"年化複合成長 (CAGR): +{sm['CAGR (%)']:.1f}% (大盤 +{bm['CAGR (%)']:.1f}%)")
    print(f"歷史最大回撤 (MDD): {sm['Max Drawdown (%)']:.1f}% (大盤 {bm['Max Drawdown (%)']:.1f}%)")
    print(f"夏普比率 (Sharpe): {sm['Sharpe Ratio']:.2f} (大盤 {bm['Sharpe Ratio']:.2f})")
    print(f"卡瑪比率 (Calmar): {sm['Calmar Ratio']:.2f} (大盤 {bm['Calmar Ratio']:.2f})")
    print(f"總完成交易次數: {sm['Total Trades']} 筆 | 勝率: {sm['Trade Win Rate (%)']:.1f}%")
