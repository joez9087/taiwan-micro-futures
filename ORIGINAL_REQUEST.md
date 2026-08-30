# Original User Request

## Initial Request — 2026-08-30T13:44:34Z

# Teamwork Project Prompt — Launched

> Status: Launched — Delegated to teamwork_preview
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full multi-agent quant and frontend developer team

構建專為「台股微型臺指期貨近月合約 (微台指, Micro TAIEX)」設計的頂級量化決策系統。系統必須在回測績效上**實質顯著超越大盤（更高累積報酬率、更高夏普比率、更低最大回撤）**，並提供**極簡約 (Minimalist) 的期貨新手友善 Web 介面**，直截了當回答新手三大核心問題：「現在多少錢可以買？」、「什麼時候適合出場（目標價）？」、「止損在哪個價格（最多賠多少）？」，並確保微台指最新期貨行情報價精準無誤，最後由獨立審計 Agent 進行 95 分以上嚴格驗收評分。

Working directory: c:\Users\JOEZ\OneDrive\桌面\python\AI agent\BTC Backtesting
Integrity mode: development

## Requirements

### R1. 精確台股微指期近月行情與宏觀數據管道 (Accurate Micro Futures & Macro Pipeline)
1. 獲取台股微型臺指期貨近月合約與加權指數歷史與最新行情（修正價格偏差，確保最新收盤點位精準對齊真實微台指近月期貨市場報價，如 ~45,896 點）。
2. 自動同步美股費城半導體 (`^SOX`) 隔夜漲跌、納斯達克 (`^IXIC`) 與美元兌台幣匯率 (`USDTWD=X`) 宏觀因子。
3. 嚴格避免未來函數（Lookahead Bias），確保跨市場與宏觀因子為前一交易日已知數據。

### R2. 實質超越大盤的微台指宏觀量化策略 (AlphaOutperform Engine)
1. 構建經過全週期（2020-2026）實證的量化波段策略，扣除期交稅（十萬分之二）與券商期貨手續費（每口 NT$15）後：
   - **總累積報酬率 > 大盤 Buy & Hold 基準**
   - **最大歷史回撤 (MDD) 顯著低於大盤**
   - **夏普比率 (Sharpe Ratio) > 1.25**
2. 結合季線 (60MA) 宏觀多空保護（大熊市 100% 空倉避險或做空）、費半動能衝擊與 ATR 自適應移動追蹤止損。

### R3. 極簡約新手專屬 Web 決策儀表板 (Minimalist Beginner UI)
1. **風格簡約大氣 (Minimalist & Clean)**：無雜亂無關資訊，配色優雅現代。
2. **新手三大核心卡片（首頁直決展示）**：
   - 🟢 **我現在可以多少錢買？**：明確標註「推薦進場點位區間」與「一口微台指需準備多少保證金 (NT$)」。
   - 🎯 **什麼時候適合出場？**：標明「第一波段目標價 TP1 (預期賺多少 NT$)」與「強勢目標價 TP2」。
   - 🛡️ **止損在哪個價格？**：標明「嚴格停損價格 SL」與「跌破此價位每口最多賠多少 NT$」。
3. **互動式新手一鍵試算機**：輸入買賣點位，一秒計算一口/多口之損益 (1 點 = NT$10)、期交稅與手續費。
4. **一鍵切換回測深度數據**：提供清晰無 bug 的淨值對比圖、回撤圖與月度績效表。

### R4. 獨立代碼審查與 95 分以上嚴格驗收評分 (Multi-Agent Quality Audit)
1. 由獨立審查 Agent 對系統架構、回測真實性、UI 易用度與價格準確性進行逐項審計。
2. 確保無任何顯示異常、無編碼報錯、UI 呈現達到 95 分以上水準。

## Acceptance Criteria

### 行情與策略回測
- [ ] 數據源與行情精準對齊台股微台指期貨近月報價。
- [ ] 策略扣除稅費後，總報酬率高於大盤基準，最大回撤低於大盤，夏普比率高於大盤。

### 極簡 Web UI 與新手功能
- [ ] UI 採簡約風格，首頁清晰回答「多少錢買」、「何時出場」、「停損在哪」，新手一眼看懂。
- [ ] 所有圖表與文字正常顯示，無截斷或亂碼。

### 獨立評審驗收
- [ ] 通過審計評分，總體評分達到 95 分以上。
