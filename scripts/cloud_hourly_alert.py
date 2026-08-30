import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.taiwan_data_loader import get_taiwan_macro_data
from src.recommendation_engine import TaiwanFuturesRecommendationEngine
from src.utils import send_bark_push

def dispatch_hourly_alert():
    bark_key = os.environ.get("BARK_KEY", "55QijEor5EwHqVqd6Cg9jJ")
    
    # 1. Fetch latest market data
    df = get_taiwan_macro_data()
    engine = TaiwanFuturesRecommendationEngine()
    rec = engine.generate_daily_recommendation(df)
    
    current_price = rec['current_index_price']
    entry_price = rec['recommended_entry_price']
    tp1_price = rec['tp1_target_price']
    sl_price = rec['stop_loss_price']
    tp1_twd = rec['tp1_twd_per_lot']
    sl_twd = rec['stop_loss_twd_per_lot']
    
    # Determine recommended lots based on capital
    recommended_lots = 1
    
    msg = (
        f"📈 目前即時報價: {current_price:,.0f} 點\n"
        f"💰 建議操作口數: {recommended_lots} 口 (微台指)\n"
        f"🎯 推薦掛單買點: {entry_price:,.0f} 點\n"
        f"🎯 第一目標價: {tp1_price:,.0f} 點 (+NT$ {tp1_twd:,.0f}/口)\n"
        f"🛡️ 嚴格停損價: {sl_price:,.0f} 點 (-NT$ {sl_twd:,.0f}/口)\n"
        f"⏱️ 持倉週期: 1~3 天短波段 (免轉倉)"
    )
    
    title = f"微台指每小時快報 ({rec['date']})"
    success = send_bark_push(msg, title=title, bark_key=bark_key)
    
    if success:
        print(f"[SUCCESS] Hourly alert dispatched to Bark (Key: {bark_key[:6]}...)")
    else:
        print("[FAILED] Failed to dispatch Bark alert.")

if __name__ == "__main__":
    dispatch_hourly_alert()
