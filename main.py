from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import yfinance as yf
from datetime import datetime, timedelta

app = FastAPI(title="股票数据服务", version="1.0.0")


def to_yf_symbol(symbol: str) -> str:
    """把 A 股代码转成 yfinance 格式"""
    if symbol.isdigit():
        if symbol.startswith("6"):
            return symbol + ".SS"   # 沪市
        elif symbol.startswith(("0", "3")):
            return symbol + ".SZ"   # 深市
        else:
            return symbol + ".SS"
    return symbol  # 美股直接返回


@app.get("/")
def root():
    return {"status": "ok", "message": "股票数据服务运行中"}


@app.get("/stock/realtime")
def get_realtime(symbol: str = Query(...)):
    try:
        yf_symbol = to_yf_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        info = ticker.fast_info
        hist = ticker.history(period="2d")
        if hist.empty:
            return JSONResponse(status_code=400, content={"error": "暂无数据，可能休市中"})
        latest = hist.iloc[-1]
        prev   = hist.iloc[-2] if len(hist) > 1 else latest
        change_pct = round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
        return {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "price": round(float(latest["Close"]), 2),
            "change_pct": change_pct,
            "volume": int(latest["Volume"]),
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/stock/indicators")
def get_indicators(symbol: str = Query(...)):
    try:
        yf_symbol = to_yf_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="6mo")   # 获取6个月历史
        if df.empty:
            return JSONResponse(status_code=400, content={"error": "暂无数据，可能休市中"})

        close = df["Close"]

        ma5  = round(float(close.rolling(5).mean().iloc[-1]), 2)
        ma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        ma60 = round(float(close.rolling(60).mean().iloc[-1]), 2)

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = round(float(100 - (100 / (1 + gain / loss)).iloc[-1]), 2)

        ema12       = close.ewm(span=12).mean()
        ema26       = close.ewm(span=26).mean()
        macd_line   = round(float((ema12 - ema26).iloc[-1]), 4)
        signal_line = round(float((ema12 - ema26).ewm(span=9).mean().iloc[-1]), 4)

        trend = "上升" if ma5 > ma20 > ma60 else ("下降" if ma5 < ma20 < ma60 else "震荡")

        return {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "current_price": round(float(close.iloc[-1]), 2),
            "ma5": ma5, "ma20": ma20, "ma60": ma60,
            "rsi_14": rsi,
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": round(macd_line - signal_line, 4),
            "trend": trend,
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)