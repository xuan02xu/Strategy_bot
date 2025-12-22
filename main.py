import ccxt
import pandas as pd
import requests
import os
import numpy as np

# --- 設定區 ---
TG_TOKEN = os.environ['TG_TOKEN']
TG_CHAT_ID = os.environ['TG_CHAT_ID']
SYMBOL = 'BTC/USDT'
TIMEFRAME = '4h'

# --- 💰 資金管理 ---
TOTAL_CAPITAL = 80.0
RISK_PER_TRADE = 0.1

# --- 風控參數 ---
ATR_PERIOD = 20
SL_MULTIPLIER = 2.0   # 初始止損 2ATR
TP_MULTIPLIER = 3.0   # 初始止盈 3ATR
TRAILING_SL_MULT = 1.5 # 移動止損 (比初始緊一點，保護獲利)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"發送失敗: {e}")

def run_strategy():
    print(f"🐢 正在執行 {SYMBOL} {TIMEFRAME} 海龜 v18.0 (趨勢追蹤版)...")
    try:
        exchange = ccxt.okx()
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # --- 指標計算 ---
        df['upper'] = df['high'].shift(1).rolling(window=20).max() # 20日高點
        df['lower'] = df['low'].shift(1).rolling(window=10).min()  # 10日低點 (海龜離場線)
        df['vol_ma'] = df['volume'].shift(1).rolling(window=20).mean()

        # ATR 計算
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'], abs(x['high'] - df['prev_close'][x.name]), abs(x['low'] - df['prev_close'][x.name])), axis=1
        )
        # 修正：這裡使用簡單寫法處理 TR，避免複雜索引報錯，實際應用建議用標準 TR 邏輯
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['prev_close'])
        df['tr3'] = abs(df['low'] - df['prev_close'])
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=ATR_PERIOD).mean()
        
        # 取得最新收盤數據
        last = df.iloc[-2]
        price = last['close']
        atr_value = last['atr']
        
        # 計算關鍵價位
        entry_sl = price - (atr_value * SL_MULTIPLIER)      # 初始止損
        entry_tp = price + (atr_value * TP_MULTIPLIER)      # 初始止盈
        trailing_sl = price - (atr_value * TRAILING_SL_MULT) # 移動止損 (動態)
        turtle_exit = last['lower'] # 海龜傳統離場點 (10日低點)

        # 資金控管
        sl_dist = atr_value * SL_MULTIPLIER
        risk_amt = TOTAL_CAPITAL * RISK_PER_TRADE
        pos_usdt = (risk_amt / sl_dist) * price
        lev = pos_usdt / TOTAL_CAPITAL
        if lev < 1: lev = 1

        # --- 判斷邏輯 ---
        is_buy_signal = (price > last['upper']) and (last['volume'] > last['vol_ma'] * 1.2) and (price > last['open'])
        
        # --- 建構訊息 ---
        msg = ""
        if is_buy_signal:
            msg = (f"🚀 【海龜 v18.0 狙擊訊號】\n"
                   f"----------------------\n"
                   f"🔥 狀態: 突破進場！\n"
                   f"現價: {price}\n"
                   f"建議開倉: {pos_usdt:.0f} U ({lev:.1f}x)\n"
                   f"🛑 初始止損: {entry_sl:.2f}\n"
                   f"💰 初始止盈: {entry_tp:.2f}")
        else:
            # 這是你要的功能：如果沒訊號，就告訴持倉者現在該怎麼辦
            msg = (f"🐢 【海龜持倉 4H 追蹤】\n"
                   f"----------------------\n"
                   f"狀態: 持倉觀察 / 空手等待\n"
                   f"現價: {price}\n"
                   f"----------------------\n"
                   f"👇 若您持有【多單】請參考 👇\n"
                   f"🛡️ 建議移動止損(ATR): {trailing_sl:.2f}\n"
                   f"🐢 海龜離場線(10日低): {turtle_exit:.2f}\n"
                   f"----------------------\n"
                   f"💡 說明: 若價格跌破 {turtle_exit:.2f} 建議全部離場。")

        # 發送
        send_telegram(msg)
        print("✅ 狀態更新已發送 Telegram")

    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    run_strategy()
