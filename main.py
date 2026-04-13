from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import akshare as ak
import yfinance as yf
from datetime import datetime, timedelta

app = FastAPI(title="股票数据服务", version="1.0.0")

@app.get("/")
def root():
    return {"status": "ok", "message": "股票数据服务运行中"}

@app.get("/stock/realtime")
def get_realtime(symbol: str = Query(..., description="股票代码，如 000001 或 AAPL")):
    try:
        if symbol.isdigit():
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == symbol].iloc[0]
            return {
                "symbol": symbol,
                "name": row['名称'],
                "price": float(row['最新价']),
                "change_pct": float(row['涨跌幅']),
                "volume": float(row['成交量']),
            }
        else:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return {
                "symbol": symbol,
                "price": float(info.last_price),
                "change_pct": round((info.last_price - info.previous_close) / info.previous_close * 100, 2),
            }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/stock/indicators")
def get_indicators(symbol: str = Query(...)):
    try:
        if symbol.isdigit():
            df = ak.stock_zh_a_hist(
                symbol=symbol, period="daily",
                start_date=(datetime.now() - timedelta(days=120)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq"
            )
            close = df['收盘']
        else:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="120d")
            close = df['Close']

        ma5  = float(close.rolling(5).mean().iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1])

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = float(100 - (100 / (1 + gain / loss)).iloc[-1])

        ema12       = close.ewm(span=12).mean()
        ema26       = close.ewm(span=26).mean()
        macd_line   = float((ema12 - ema26).iloc[-1])
        signal_line = float((ema12 - ema26).ewm(span=9).mean().iloc[-1])

        return {
            "symbol": symbol,
            "current_price": float(close.iloc[-1]),
            "ma5": round(ma5, 2), "ma20": round(ma20, 2), "ma60": round(ma60, 2),
            "rsi_14": round(rsi, 2),
            "macd": round(macd_line, 4),
            "macd_signal": round(signal_line, 4),
            "macd_histogram": round(macd_line - signal_line, 4),
            "trend": "上升" if ma5 > ma20 > ma60 else ("下降" if ma5 < ma20 < ma60 else "震荡")
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)