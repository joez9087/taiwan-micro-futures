import numpy as np
import pandas as pd
from datetime import datetime

try:
    from .taiwan_data_loader import get_taiwan_macro_data
    from .taiwan_macro_strategy import TaiwanShortSwingAlphaStrategy
except (ImportError, ValueError):
    from taiwan_data_loader import get_taiwan_macro_data
    from taiwan_macro_strategy import TaiwanShortSwingAlphaStrategy

class TaiwanFuturesRecommendationEngine:
    """
    Taiwan Micro Futures (微台指) Single-Price Recommendation & Active Position Engine.
    """
    def __init__(self, point_value=10.0, initial_margin_per_lot=18000.0, safe_capital_per_lot=50000.0):
        self.point_value = point_value
        self.initial_margin_per_lot = initial_margin_per_lot
        self.safe_capital_per_lot = safe_capital_per_lot
        self.strategy = TaiwanShortSwingAlphaStrategy()

    def generate_daily_recommendation(self, df_raw=None):
        if df_raw is None:
            df_raw = get_taiwan_macro_data()
            
        df_sig = self.strategy.generate_signals(df_raw)
        latest_row = df_sig.iloc[-1]
        latest_date = df_sig.index[-1]
        
        c = float(latest_row['tw_close'])
        e_macro = float(latest_row['tw_ema_macro'])
        e_fast = float(latest_row['tw_ema_fast'])
        atr = float(latest_row['atr_14'])
        sox_r = float(latest_row['sox_ret_1d'])
        target_pos = float(latest_row['target_position'])
        
        # Exact Single Recommended Entry Price (No range!)
        recommended_entry_price = round(c - (0.15 * atr), 0)
        
        # Stop Loss & Take Profit
        sl_price = round(recommended_entry_price - (1.4 * atr), 0)
        tp1_price = round(recommended_entry_price + (1.8 * atr), 0)
        tp2_price = round(recommended_entry_price + (3.0 * atr), 0)
        
        sl_pts = abs(recommended_entry_price - sl_price)
        tp1_pts = abs(tp1_price - recommended_entry_price)
        tp2_pts = abs(tp2_price - recommended_entry_price)
        
        rr_ratio = round(tp1_pts / (sl_pts + 1e-6), 2)
        
        direction = "LONG" if target_pos > 0 or c > e_macro else "WAIT"
        direction_label = "🟢 建議做多 (BUY / LONG)" if direction == "LONG" else "⚪ 建議觀望 (WAIT / 抱現金)"
        
        return {
            "date": latest_date.strftime("%Y-%m-%d"),
            "current_index_price": c,
            "direction": direction,
            "direction_label": direction_label,
            "action_desc": "宏觀趨勢偏多，費半走強，建議限價掛單做多 (持倉 1~3 天免轉倉)",
            "recommended_entry_price": recommended_entry_price, # Single exact number!
            "stop_loss_price": sl_price,
            "stop_loss_points": int(sl_pts),
            "stop_loss_twd_per_lot": sl_pts * self.point_value,
            "tp1_target_price": tp1_price,
            "tp1_points": int(tp1_pts),
            "tp1_twd_per_lot": tp1_pts * self.point_value,
            "tp2_target_price": tp2_price,
            "tp2_points": int(tp2_pts),
            "tp2_twd_per_lot": tp2_pts * self.point_value,
            "risk_reward_ratio": rr_ratio,
            "current_atr": atr,
            "initial_margin": self.initial_margin_per_lot,
            "safe_capital": self.safe_capital_per_lot
        }

    def evaluate_active_position(self, entry_price: float, holding_days: int = 1, current_price: float = 45896.0, atr: float = 700.0):
        """
        Evaluate an existing active position: compute today's dynamic SL/TP and guidance.
        """
        pnl_pts = current_price - entry_price
        pnl_twd = pnl_pts * self.point_value
        
        # Trailing Stop moves up as holding progresses
        base_sl = entry_price - (1.4 * atr)
        dynamic_sl = max(base_sl, current_price - (1.2 * atr)) if pnl_pts > (1.0 * atr) else base_sl
        dynamic_tp1 = entry_price + (1.8 * atr)
        dynamic_tp2 = entry_price + (3.0 * atr)
        
        if current_price <= dynamic_sl:
            status = "DANGER_SL"
            guidance = "⚠️ 已跌破今日停損價！請立即手動平倉出場，嚴格控制風險！"
        elif current_price >= dynamic_tp1:
            status = "SUCCESS_TP"
            guidance = "🎉 已達到第一停利目標！建議先平倉 50% 鎖定利潤，其餘設保本停利！"
        elif holding_days >= 4:
            status = "TIME_EXIT"
            guidance = "⏱️ 已持倉達 4 天！為避免跨月轉倉，建議今日趁勢獲利平倉結算！"
        else:
            status = "HOLDING"
            guidance = "🟢 獲利續抱中！未觸及停損/停利，符合 1~3 天短波段節奏，安心持倉。"
            
        return {
            "entry_price": entry_price,
            "current_price": current_price,
            "pnl_pts": round(pnl_pts, 1),
            "pnl_twd": round(pnl_twd, 0),
            "dynamic_sl": round(dynamic_sl, 0),
            "dynamic_tp1": round(dynamic_tp1, 0),
            "dynamic_tp2": round(dynamic_tp2, 0),
            "holding_days": holding_days,
            "status": status,
            "guidance": guidance
        }

if __name__ == "__main__":
    engine = TaiwanFuturesRecommendationEngine()
    rec = engine.generate_daily_recommendation()
    print("Exact Entry Price:", rec['recommended_entry_price'])
    pos_eval = engine.evaluate_active_position(entry_price=45850.0, holding_days=2)
    print("Position PnL TWD:", pos_eval['pnl_twd'])
