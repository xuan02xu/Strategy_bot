import ccxt
import pandas as pd
import requests
import os

# --- 設定區 (這些會從 GitHub 後台讀取，不用改) ---
TG_TOKEN = os.environ['TG_TOKEN']
TG_CHAT_ID = os.environ['TG_CHAT_ID']
SYMBOL = 'BTC/USDT'
TIMEFRAME = '4h'

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": message
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"發送失敗: {e}")

def run_strategy():
    print(f"🐢 正在檢查 {SYMBOL} {TIMEFRAME} 海龜 v16.0 訊號...")
    try:
        # 連接 OKX (只讀取數據，不需要 API Key)
        exchange = ccxt.okx()
        
        # 抓取最近 100 根 K 線 (確保數據足夠計算 20MA)
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # v16.0 策略計算
        # 上軌：過去 20 根 K 棒的最高價 (不含當前這根，所以 shift 1)
        df['upper'] = df['high'].shift(1).rolling(window=20).max()
        # 成交量均線：過去 20 根的平均量
        df['vol_ma'] = df['volume'].shift(1).rolling(window=20).mean()
        
        # 取得「剛收盤」的那根 K 棒 (倒數第二根，因為 -1 是還沒收盤的)
        last_closed = df.iloc[-2]
        
        # 數值提取
        price = last_closed['close']
        open_price = last_closed['open']
        upper = last_closed['upper']
        vol = last_closed['volume']
        vol_limit = last_closed['vol_ma'] * 1.2
        
        print(f"📊 收盤價: {price} | 上軌阻力: {upper} | 成交量: {vol} (門檻: {vol_limit})")

        # 觸發條件 (v16.0 高勝率版)：
        # 1. 價格突破 20日新高
        # 2. 成交量 > 1.2倍均量 (爆量)
        # 3. 收盤價 > 開盤價 (實體陽線)
        if (price > upper) and (vol > vol_limit) and (price > open_price):
            msg = (f"🐢 【海龜 v16.0 狙擊訊號】 🐢\n"
                   f"----------------------\n"
                   f"幣種: {SYMBOL}\n"
                   f"現價: {price}\n"
                   f"狀態: 🔥 突破20日新高 + 爆量！\n"
                   f"動作: 快去 BingX 開多 20U！")
            send_telegram(msg)
            print("✅ 訊號已發送！")
        else:
            print("💤 未觸發訊號，繼續等待...")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    run_strategy()
