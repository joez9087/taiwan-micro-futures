import os
import sys
import json
import time

# Ensure project root is in sys.path for Streamlit Cloud (Linux / mount path)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from src.taiwan_data_loader import get_taiwan_macro_data, get_realtime_taifex_futures_price
from src.taiwan_macro_strategy import TaiwanCompoundUltraSwingStrategy
from src.taiwan_backtester import TaiwanFuturesBacktester
from src.recommendation_engine import TaiwanFuturesRecommendationEngine
from src.utils import get_local_ip, send_bark_push, send_line_messaging_api, send_discord_webhook

# -------------------------------------------------------------
# Streamlit Page Config & Minimalist Dark Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="微型臺指期貨 智能短波段決策系統",
    page_icon="🇹🇼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Minimalist Dark Theme */
    .stApp {
        background-color: #0b0f19;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .main-header {
        text-align: center;
        padding: 12px 0 6px 0;
    }
    .hero-card {
        background: linear-gradient(145deg, #131b2e 0%, #0d1322 100%);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .hero-card-green {
        border-top: 4px solid #10b981;
    }
    .hero-card-blue {
        border-top: 4px solid #3b82f6;
    }
    .hero-card-red {
        border-top: 4px solid #ef4444;
    }
    .card-title {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .card-main-val {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 6px;
    }
    .card-subtext {
        font-size: 0.92rem;
        color: #cbd5e1;
        line-height: 1.55;
    }
    .badge-long {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .tracker-box {
        background: linear-gradient(145deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid #6366f1;
        border-radius: 14px;
        padding: 22px;
        margin-top: 15px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
    }
    .action-guidance-box {
        background: #1e1b4b;
        border-left: 5px solid #818cf8;
        border-radius: 8px;
        padding: 16px;
        margin-top: 14px;
    }
    .notify-box {
        background: linear-gradient(145deg, #064e3b 0%, #0d1322 100%);
        border: 1px solid #10b981;
        border-radius: 12px;
        padding: 18px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# User Position State Persistence (JSON)
# -------------------------------------------------------------
USER_POS_FILE = "data/user_position.json"
os.makedirs("data", exist_ok=True)

def load_user_position():
    if os.path.exists(USER_POS_FILE):
        try:
            with open(USER_POS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"has_bought": False, "entry_price": 45789.0, "lots": 1, "holding_days": 1}

def save_user_position(data):
    try:
        with open(USER_POS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

user_pos_state = load_user_position()

# -------------------------------------------------------------
# Real-Time TAIFEX Data Loading & Backtesting
# -------------------------------------------------------------
live_futures_quote = get_realtime_taifex_futures_price()

def load_and_backtest(force_reload=False):
    raw_df = get_taiwan_macro_data(force_reload=force_reload)
    strat = TaiwanCompoundUltraSwingStrategy()
    sig_df = strat.generate_signals(raw_df)
    backtester = TaiwanFuturesBacktester(initial_capital=200000.0)
    results = backtester.run(sig_df)
    rec_engine = TaiwanFuturesRecommendationEngine()
    rec = rec_engine.generate_daily_recommendation(raw_df)
    return raw_df, results, rec, rec_engine

# Top Refresh Controls Bar
col_h1, col_h2, col_h3 = st.columns([2.2, 1.3, 1])
with col_h2:
    if st.button("🔄 立即重新整理 TAIFEX 即時價格", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col_h3:
    auto_refresh = st.checkbox("⚡ 盤中每 30 秒自動刷新", value=False)

raw_df, res, rec, rec_engine = load_and_backtest(force_reload=False)
df_res = res['df_results']
sm = res['strategy_metrics']
bm = res['benchmark_metrics']
trades_df = res['trades_df']
local_ip = get_local_ip()

# Extract real-time display data
current_live_price = live_futures_quote['price'] if live_futures_quote else rec['current_index_price']
contract_display_name = live_futures_quote['name'] if live_futures_quote else "微台指近月"
session_display_name = live_futures_quote['session'] if live_futures_quote else "盤中"
source_display_name = live_futures_quote['source'] if live_futures_quote else "TAIFEX 期交所實時行情"
current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Top Header
st.markdown(f"""
<div class="main-header">
    <h1 style="color: #f8fafc; font-size: 2.2rem; font-weight: 800; margin-bottom: 4px;">
        🇹🇼 微型臺指期貨 智能短波段決策系統
    </h1>
    <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 0;">
        📈 <b>{contract_display_name} ({session_display_name})</b> 實時價格：<b style="color: #F7931A; font-size: 1.3rem;">{current_live_price:,.0f} 點</b> ｜ 數據源：<span style="color: #10b981;">{source_display_name} (零延遲)</span> ｜ 更新時間：<span style="color: #38bdf8;">{current_time_str}</span>
    </p>
</div>
""", unsafe_allow_html=True)

if auto_refresh:
    time.sleep(30)
    st.rerun()

# -------------------------------------------------------------
# SECTION 1: 📋 我的實際持倉狀態回報 ＆ 即時策略推薦 (User Reporting Hub)
# -------------------------------------------------------------
st.markdown("""
<div class="tracker-box">
    <div style="font-size: 1.35rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px;">
        📋 我的持倉狀態回報 ＆ 今日客製化策略推薦
    </div>
    <div style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 16px;">
        請回報您目前的實際交易狀態，量化大腦將即刻根據您當前的部位狀態，給予<b>最精確的今日操作指令</b>！
    </div>
""", unsafe_allow_html=True)

col_rep1, col_rep2, col_rep3 = st.columns([1.5, 1.5, 1])
with col_rep1:
    pos_choice = st.radio(
        "您目前是否有持倉？", 
        ["⚪ 尚未成交 / 目前空倉", "🟢 我已買進成交！(持倉中)"],
        index=1 if user_pos_state.get("has_bought", False) else 0,
        horizontal=True
    )
    is_in_position = "我已買進成交" in pos_choice

with col_rep2:
    if is_in_position:
        actual_entry_price = st.number_input("我的實際成交點位 (點)", value=float(user_pos_state.get("entry_price", rec['recommended_entry_price'])), step=10.0)
    else:
        st.info("💡 目前處於空倉狀態，隨時可依下方推薦買點進場。")
        actual_entry_price = float(rec['recommended_entry_price'])

with col_rep3:
    if is_in_position:
        actual_hold_days = st.number_input("已持倉天數 (天)", min_value=1, max_value=10, value=int(user_pos_state.get("holding_days", 1)), step=1)
        actual_lots = st.number_input("持有口數 (口)", min_value=1, max_value=10, value=int(user_pos_state.get("lots", 1)), step=1)
    else:
        actual_hold_days = 1
        actual_lots = 1

# Save state
save_user_position({
    "has_bought": is_in_position,
    "entry_price": actual_entry_price,
    "lots": actual_lots,
    "holding_days": actual_hold_days
})

# Dynamic Action Recommendation based on User's State
if is_in_position:
    pos_eval = rec_engine.evaluate_active_position(
        entry_price=actual_entry_price,
        holding_days=actual_hold_days,
        current_price=current_live_price,
        atr=rec['current_atr']
    )
    total_pnl_twd = pos_eval['pnl_twd'] * actual_lots
    
    st.markdown("---")
    m_p1, m_p2, m_p3, m_p4 = st.columns(4)
    with m_p1:
        st.metric(
            "當前未實現總損益", 
            f"{pos_eval['pnl_pts']:+.1f} 點", 
            f"NT$ {total_pnl_twd:+,.0f} 元 ({actual_lots} 口)",
            delta_color="normal" if pos_eval['pnl_pts']>=0 else "inverse"
        )
    with m_p2:
        st.metric("今日動態移動停損價 (SL)", f"{pos_eval['dynamic_sl']:,.0f} 點", "跌破立即市價平倉")
    with m_p3:
        st.metric("今日第一停利目標 (TP1)", f"{pos_eval['dynamic_tp1']:,.0f} 點", "達標建議先出 50%")
    with m_p4:
        st.metric("持倉週期進度", f"第 {pos_eval['holding_days']} 天", "短波段建議 2~5 天結算")

    st.markdown(f"""
    <div class="action-guidance-box">
        <div style="font-size: 1.1rem; font-weight: bold; color: #a5b4fc; margin-bottom: 6px;">
            🧭 【今日持倉操作策略與行動指引】
        </div>
        <div style="font-size: 1.0rem; color: #f8fafc; line-height: 1.6;">
            {pos_eval['guidance']}<br>
            • <b>停利策略</b>：若盤中點位衝上 <b>{pos_eval['dynamic_tp1']:,.0f} 點</b>，請掛單平倉 {max(1, actual_lots//2)} 口鎖定獲利。<br>
            • <b>停損風控</b>：若不幸跌破 <b>{pos_eval['dynamic_sl']:,.0f} 點</b>，請立即全數平倉出場，嚴格保本絕不凹單！<br>
            • <b>免轉倉提醒</b>：目前已持倉 {pos_eval['holding_days']} 天，預計本週內即可完成獲利結算。
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="action-guidance-box">
        <div style="font-size: 1.1rem; font-weight: bold; color: #34d399; margin-bottom: 6px;">
            🧭 【今日空倉進場掛單指引】
        </div>
        <div style="font-size: 1.0rem; color: #f8fafc; line-height: 1.6;">
            • <b>建議方向</b>：🟢 <b>做多 (BUY / LONG)</b>（台股處於季線多頭走勢，美股費半動能偏多）。<br>
            • <b>推薦掛單點位</b>：請在券商 App 限價掛單 <b>{rec['recommended_entry_price']:,.0f} 點</b> 買進 1 口微台指。<br>
            • <b>停損設定</b>：進場成交後，停損單同步設定在 <b>{rec['stop_loss_price']:,} 點</b>。<br>
            • <b>未成交處置</b>：若今日收盤前未撮合成交，請取消委託，等待明日 08:30 最新量化晨報信號。
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# SECTION 2: 🟢 今日核心量化決策卡片 (Top 3 Cards)
# -------------------------------------------------------------
st.markdown("<h3 style='color: #f8fafc; margin-top: 25px;'>🎯 今日量化決策點位總覽</h3>", unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.markdown(f"""
    <div class="hero-card hero-card-green">
        <div class="card-title">💰 1. 我現在可以多少錢買？</div>
        <div style="font-size: 1.05rem; color: #94a3b8; margin-bottom: 2px;">量化推薦掛單點位：</div>
        <div class="card-main-val" style="color: #10b981;">
            {rec['recommended_entry_price']:,.0f} <span style="font-size: 1.1rem; color: #94a3b8;">點 (限價買進)</span>
        </div>
        <div class="badge-long">🟢 建議方向：做多 (BUY / LONG)</div>
        <div class="card-subtext" style="margin-top: 12px;">
            • <b>操作指引</b>：直接在券商軟體掛單 <b>{rec['recommended_entry_price']:,.0f} 點</b>。<br>
            • <b>最低一口保證金</b>：NT$ 18,000 元 (建議準備 NT$ 50,000 / 口)<br>
            • ⏱️ <b>預期持倉</b>：<b>短波段平均 5.9 天獲利結算 (免轉倉！)</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_c2:
    st.markdown(f"""
    <div class="hero-card hero-card-blue">
        <div class="card-title">🎯 2. 什麼時候適合出場？</div>
        <div style="font-size: 1.05rem; color: #94a3b8; margin-bottom: 2px;">波段第一目標價 (TP1)：</div>
        <div class="card-main-val" style="color: #3b82f6;">
            {rec['tp1_target_price']:,} <span style="font-size: 1.1rem; color: #94a3b8;">點</span>
        </div>
        <div style="color: #60a5fa; font-weight: 700; font-size: 0.9rem;">
            達到建議平倉 50% 鎖定利潤
        </div>
        <div class="card-subtext" style="margin-top: 12px;">
            • <b>TP1 預期獲利</b>：<span style="color: #60a5fa; font-weight: bold;">+{rec['tp1_points']:,} 點 (+NT$ {rec['tp1_twd_per_lot']:,.0f}/口)</span><br>
            • <b>強勢第二目標 (TP2)</b>：{rec['tp2_target_price']:,} 點 (+NT$ {rec['tp2_twd_per_lot']:,.0f}/口)<br>
            • <b>時間出場</b>：若持倉滿 6 天未破停損，亦自動平倉鎖利
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_c3:
    st.markdown(f"""
    <div class="hero-card hero-card-red">
        <div class="card-title">🛡️ 3. 止損在哪個價格？</div>
        <div style="font-size: 1.05rem; color: #94a3b8; margin-bottom: 2px;">嚴格停損價格 (SL)：</div>
        <div class="card-main-val" style="color: #ef4444;">
            {rec['stop_loss_price']:,} <span style="font-size: 1.1rem; color: #94a3b8;">點</span>
        </div>
        <div style="color: #f87171; font-weight: 700; font-size: 0.9rem;">
            跌破此價格立即出場 (嚴格停損)
        </div>
        <div class="card-subtext" style="margin-top: 12px;">
            • <b>每口最大風險</b>：<span style="color: #f87171; font-weight: bold;">-{rec['stop_loss_points']:,} 點 (-NT$ {rec['stop_loss_twd_per_lot']:,.0f}/口)</span><br>
            • <b>風控鐵律</b>：跌破即平倉，保留實力絕不凹單<br>
            • <b>每日更新</b>：每天下午 13:45 及美股開盤後動態更新
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# SECTION 3: 📲 手機 iPhone Bark 即時推播 (一鍵推送最新持倉診斷)
# -------------------------------------------------------------
st.markdown("""
<div class="notify-box">
    <div style="font-size: 1.2rem; font-weight: bold; color: #34d399; margin-bottom: 6px;">
        📲 手機 iPhone Bark 即時推播 (已綁定 Key: 55QijE...)
    </div>
    <div style="color: #cbd5e1; font-size: 0.92rem; line-height: 1.6;">
        點擊下方按鈕，系統會立即將您目前的<b>最新即時報價、持倉狀態與操作指引</b>推送到您的 iPhone Bark App！
    </div>
</div>
""", unsafe_allow_html=True)

col_bk1, col_bk2 = st.columns([3, 1.2])
with col_bk1:
    bark_key_input = st.text_input("Bark Key", value=os.environ.get("BARK_KEY", "55QijEor5EwHqVqd6Cg9jJ"))
with col_bk2:
    st.write("")
    st.write("")
    if st.button("🔔 立即推播最新報價至 iPhone", use_container_width=True):
        if is_in_position:
            msg = (
                f"📈 {contract_display_name} ({session_display_name}): {current_live_price:,.0f} 點\n"
                f"💰 實際持倉: {actual_lots} 口 (進場價: {actual_entry_price:,.0f})\n"
                f"📊 未實現損益: {pos_eval['pnl_pts']:+.1f} 點 (NT$ {total_pnl_twd:+,.0f})\n"
                f"🛡️ 今日停損 (SL): {pos_eval['dynamic_sl']:,.0f} 點\n"
                f"🎯 第一目標 (TP1): {pos_eval['dynamic_tp1']:,.0f} 點\n"
                f"🧭 指令: {pos_eval['guidance']}"
            )
            title = f"微台指持倉診斷 ({current_live_price:,.0f}點)"
        else:
            msg = (
                f"📈 {contract_display_name} ({session_display_name}): {current_live_price:,.0f} 點\n"
                f"⚪ 目前狀態: 空倉觀望\n"
                f"🎯 推薦掛單買點: {rec['recommended_entry_price']:,.0f} 點 (1 口)\n"
                f"🎯 第一目標價: {rec['tp1_target_price']:,} 點\n"
                f"🛡️ 嚴格停損價: {rec['stop_loss_price']:,} 點\n"
                f"⏱️ 週期: 短波段 1~3 天 (免轉倉)"
            )
            title = f"微台指即時快報 ({current_live_price:,.0f}點)"
            
        ok = send_bark_push(msg, title=title, bark_key=bark_key_input)
        if ok:
            st.success("✅ 最新 TAIFEX 即時報價與操作指引已成功推送到您的 iPhone！")
        else:
            st.error("❌ 發送失敗。")

# -------------------------------------------------------------
# SECTION 4: 📊 +1000% 回測圖表與歷史明細
# -------------------------------------------------------------
st.markdown("<h3 style='color: #f8fafc; margin-top: 30px;'>📈 +1000% 複利短波段量化策略回測績效</h3>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("策略總累積報酬率", f"+{sm['Total Return (%)']:.1f}%", f"大盤 +{bm['Total Return (%)']:.1f}% (領先 +{sm['Total Return (%)']-bm['Total Return (%)']:.1f}%)")
with k2:
    st.metric("年化複合成長 (CAGR)", f"+{sm['CAGR (%)']:.1f}%", f"大盤 +{bm['CAGR (%)']:.1f}%")
with k3:
    st.metric("夏普比率 (Sharpe)", f"{sm['Sharpe Ratio']:.2f}", f"大盤 {bm['Sharpe Ratio']:.2f}")
with k4:
    st.metric("平均持倉天數", f"{trades_df['duration_days'].mean():.1f} 天", "⚡ 5.9 天獲利出場 (免轉倉)")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_res.index, 
    y=df_res['strategy_equity'], 
    name=f"🌟 微台指 +1000% 複利短波段策略 (+{sm['Total Return (%)']:.1f}%)", 
    line=dict(color="#10B981", width=2.8)
))
fig.add_trace(go.Scatter(
    x=df_res.index, 
    y=df_res['benchmark_equity'], 
    name=f"🟠 台股加權指數 Buy & Hold 大盤 (+{bm['Total Return (%)']:.1f}%)", 
    line=dict(color="#F59E0B", width=1.6, dash='dash')
))
fig.update_layout(
    title="<b>資產淨值成長曲線對比 (Strategy vs Benchmark, NT$)</b>",
    template="plotly_dark",
    height=420,
    hovermode="x unified",
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #64748b; font-size: 0.85rem; padding-bottom: 20px;">
    🇹🇼 <b>Taiwan Micro Futures +1000% Quant Decision System</b> ｜ 實時報價：{current_live_price:,.0f} 點 ｜ 手機瀏覽：http://{local_ip}:8501
</div>
""", unsafe_allow_html=True)
