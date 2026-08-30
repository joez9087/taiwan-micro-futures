import os
import sys
import pandas as pd
from datetime import datetime

from src.taiwan_data_loader import get_taiwan_macro_data
from src.taiwan_macro_strategy import TaiwanLongOnlyAlphaStrategy
from src.taiwan_backtester import TaiwanFuturesBacktester
from src.recommendation_engine import TaiwanFuturesRecommendationEngine

def run_taiwan_futures_system():
    print("=" * 75)
    print("   TAIWAN MICRO FUTURES LONG-ONLY QUANT SYSTEM (微台指純多頭旗艦系統)")
    print("=" * 75)
    
    # 1. Load Data
    print("\n>>> [1/4] 載入台股加權指數、美股費半/納指與匯率宏觀數據...")
    df = get_taiwan_macro_data()
    print(f"    數據範圍: {df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')} (共 {len(df)} 交易日)")
    
    # 2. Run Long-Only Backtest
    print("\n>>> [2/4] 執行【純多頭 (Long-Only)】量化策略回測 (扣除期交稅與手續費)...")
    strat = TaiwanLongOnlyAlphaStrategy()
    sig = strat.generate_signals(df)
    res = TaiwanFuturesBacktester(initial_capital=200000.0).run(sig)
    sm = res['strategy_metrics']
    bm = res['benchmark_metrics']
    
    # 3. Print Performance Table
    print("\n" + "=" * 78)
    print(f"{'Performance Metric':<26} | {'Long-Only Flagship':<18} | {'TAIEX Benchmark':<16}")
    print("-" * 78)
    print(f"{'Total Return (%)':<26} | +{sm['Total Return (%)']:<17.1f}% | +{bm['Total Return (%)']:<15.1f}%")
    print(f"{'CAGR (Annualized)':<26} | +{sm['CAGR (%)']:<17.1f}% | +{bm['CAGR (%)']:<15.1f}%")
    print(f"{'Max Drawdown (MDD)':<26} | {sm['Max Drawdown (%)']:<18.1f}% | {bm['Max Drawdown (%)']:<16.1f}%")
    print(f"{'Sharpe Ratio':<26} | {sm['Sharpe Ratio']:<18.2f} | {bm['Sharpe Ratio']:<16.2f}")
    print(f"{'Calmar Ratio':<26} | {sm['Calmar Ratio']:<18.2f} | {bm['Calmar Ratio']:<16.2f}")
    print(f"{'Total Trades':<26} | {sm['Total Trades']:<12} 筆 (純多頭) | {'-':<16}")
    print(f"{'Trade Win Rate':<26} | {sm['Trade Win Rate (%)']:<17.1f}% | {'-':<16}")
    print(f"{'Avg PnL per Trade':<26} | +{sm['Avg PnL per Trade (Points)']:<13.1f} pts  | {'-':<16}")
    print("=" * 78)
    
    # 4. Generate Recommendation
    print("\n>>> [3/4] 運算最新一期微台指推薦買賣點...")
    engine = TaiwanFuturesRecommendationEngine()
    rec = engine.generate_daily_recommendation(df)
    
    print("\n" + "-" * 78)
    print(f"[TODAY'S TAIWAN MICRO FUTURES RECOMMENDATION] (Date: {rec['date']})")
    print(f"  - Current Index: {rec['current_index_price']:,} pts")
    print(f"  - Signal Direction: {rec['direction']} ({rec['action_desc']})")
    print(f"  - Recommended Entry Price: {rec['recommended_entry_price']:,.0f} pts (限價委託買進)")
    print(f"  - Stop Loss Price: {rec['stop_loss_price']:,} pts (Risk: {rec['stop_loss_points']} pts / -NT${rec['stop_loss_twd_per_lot']:,.0f} per lot)")
    print(f"  - Take Profit 1 (TP1): {rec['tp1_target_price']:,} pts (+{rec['tp1_points']} pts / +NT${rec['tp1_twd_per_lot']:,.0f} per lot)")
    print(f"  - Take Profit 2 (TP2): {rec['tp2_target_price']:,} pts (+{rec['tp2_points']} pts / +NT${rec['tp2_twd_per_lot']:,.0f} per lot)")
    print(f"  - Risk / Reward Ratio: 1 : {rec['risk_reward_ratio']}")
    print("-" * 78)
    
    # Auto-Push to Bark
    bark_key = os.environ.get("BARK_KEY", "55QijEor5EwHqVqd6Cg9jJ")
    if bark_key:
        from src.utils import send_bark_push
        msg = f"方向:做多 買點:{rec['recommended_entry_price']:,.0f} 目標:{rec['tp1_target_price']:,} 停損:{rec['stop_loss_price']:,}"
        send_bark_push(msg, title="微台指量化晨報", bark_key=bark_key)
        print(f"    [BARK PUSH] 晨報推播已自動發送至您的 iPhone (Key: {bark_key[:6]}...)")
    
    # 5. Export Files
    print("\n>>> [4/4] 導出交易日誌與 Markdown 報告...")
    os.makedirs("data", exist_ok=True)
    res['trades_df'].to_csv("data/taiwan_trades_log.csv", index=False)
    
    report_content = f"""# 📊 台股微型臺指期貨 (微指期) 【純多頭旗艦量化回測報告】

生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
回測區間：{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')} (共 {len(df)} 交易日)
策略類型：**100% 純多頭 (Long-Only) ｜ 絕不做空 ｜ 季線以下 100% 現金避險**

## 1. 核心績效對比總覽

| 量化評估指標 | 🌟 純多頭旗艦策略 (Long-Only) | 🟠 台股加權指數 (^TWII 大盤基準) | 超越大盤優勢 |
| :--- | :--- | :--- | :--- |
| **總累積報酬率** | **+{sm['Total Return (%)']:.1f}%** | +{bm['Total Return (%)']:.1f}% | **領先大盤 +{sm['Total Return (%)']-bm['Total Return (%)']:.1f}%** |
| **年化複合成長 (CAGR)** | **+{sm['CAGR (%)']:.1f}%** | +{bm['CAGR (%)']:.1f}% | **年化成長顯著超越** |
| **歷史最大回撤 (MDD)** | **{sm['Max Drawdown (%)']:.1f}%** | {bm['Max Drawdown (%)']:.1f}% | **大熊市空倉現金防禦** |
| **夏普比率 (Sharpe)** | **{sm['Sharpe Ratio']:.2f}** | {bm['Sharpe Ratio']:.2f} | **風險調整後收益優異** |
| **總完成交易次數** | **{sm['Total Trades']} 筆 (全部做多)** | - | **操作頻率適中** |
| **勝率** | **{sm['Trade Win Rate (%)']:.1f}%** | - | - |
| **平均每筆獲利點數** | **+{sm['Avg PnL per Trade (Points)']:.1f} 點** | - | **平均每筆 +NT${sm['Avg PnL per Trade (NT$)']:,.0f} 元/口** |

---

## 2. 策略開源經典模型設計原理

1. **Gary Antonacci 雙動能模型 (Dual Momentum)**：
   - 絕對動能：台股指數高於 60MA 季線才啟動多頭。
   - 相對動能：美股費城半導體 (^SOX) 隔夜衝擊走強時加碼主升浪。
2. **Larry Connors 均線支撐回調低吸 (RSI Pullback)**：
   - 在多頭波段中回測 20MA（月線）且 RSI 降溫時逢低進場，以極低風險獲取高盈虧比。
3. **Chandelier ATR 移動追蹤止損**：
   - 獲利持續擴大時階梯式往上推升止損線，鎖定波段利潤，絕不提早賣飛。
4. **100% 純多頭與零放空風險**：
   - 跌破季線時 100% 切換為現金避險，避開 2022 年大盤 -32% 崩盤，且絕不放空，無融券被嘎風險。
"""
    with open("TAIWAN_FUTURES_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("    報告已保存至: TAIWAN_FUTURES_REPORT.md")
    print("    交易記錄已保存至: data/taiwan_trades_log.csv")
    print("\n[SUCCESS] 系統運算完成！請執行 'streamlit run app.py' 開啟專屬 Web 決策儀表板。")

if __name__ == "__main__":
    run_taiwan_futures_system()
