from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import yfinance as yf
import pandas as pd
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import warnings
warnings.filterwarnings("ignore")


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Stock Predictor API",
    description="Machine Learning based stock trend prediction",
    version="1.0.0"
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML templates
templates = Jinja2Templates(directory="templates")


# =========================================================
# HOME PAGE
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


# =========================================================
# DATA FETCH
# =========================================================

def get_data(ticker: str):

    df = yf.download(
        ticker,
        period="1y",
        auto_adjust=True,
        progress=False
    )

    if df is None or df.empty:
        return None

    # Handle yfinance MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)

    return df


# =========================================================
# FEATURE ENGINEERING
# =========================================================

def add_features(df):

    df = df.copy()

    df["Return"] = df["Close"].pct_change()

    df["MA5"] = df["Close"].rolling(5).mean()

    df["MA10"] = df["Close"].rolling(10).mean()

    df["Volatility"] = (
        df["Return"]
        .rolling(5)
        .std()
    )

    # RSI
    delta = df["Close"].diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (
        100 / (1 + rs)
    )

    # Tomorrow's movement
    df["Target"] = np.where(
        df["Close"].shift(-1) > df["Close"],
        1,
        0
    )

    df.dropna(inplace=True)

    return df


# =========================================================
# MODEL
# =========================================================

def train_and_predict(df):

    features = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "MA5",
        "MA10",
        "Volatility",
        "RSI"
    ]

    X = df[features]

    y = df["Target"]

    # Last row is prediction point
    X_train = X.iloc[:-1]

    y_train = y.iloc[:-1]

    X_current = X.iloc[-1:]

    # Scaling
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)

    X_current_scaled = scaler.transform(X_current)

    # Logistic Regression
    model = LogisticRegression(
        max_iter=1000
    )

    model.fit(
        X_train_scaled,
        y_train
    )

    # Prediction
    prediction = model.predict(
        X_current_scaled
    )[0]

    probabilities = model.predict_proba(
        X_current_scaled
    )[0]

    confidence = probabilities[prediction]

    return int(prediction), float(confidence)


# =========================================================
# SINGLE STOCK
# =========================================================

def analyze_stock(ticker):

    ticker = ticker.strip().upper()

    df = get_data(ticker)

    if df is None or df.empty:
        raise ValueError(
            f"No data found for {ticker}"
        )

    df = add_features(df)

    if len(df) < 50:
        raise ValueError(
            f"Not enough data for {ticker}"
        )

    prediction, confidence = train_and_predict(df)

    if prediction == 1:
        trend = "UP"
        signal = "BUY"
    else:
        trend = "DOWN"
        signal = "SELL"

    # Recent prices for chart
    chart_data = []

    for date, row in df.tail(90).iterrows():

        chart_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(float(row["Close"]), 2)
        })

    latest = df.iloc[-1]

    return {
        "ticker": ticker,
        "prediction": trend,
        "signal": signal,
        "confidence": round(confidence * 100, 2),
        "current_price": round(
            float(latest["Close"]), 2
        ),
        "rsi": round(
            float(latest["RSI"]), 2
        ),
        "ma5": round(
            float(latest["MA5"]), 2
        ),
        "ma10": round(
            float(latest["MA10"]), 2
        ),
        "volatility": round(
            float(latest["Volatility"] * 100), 2
        ),
        "chart": chart_data
    }


# =========================================================
# PREDICTION API
# =========================================================

@app.get("/predict")
async def predict(ticker: str):

    try:

        result = analyze_stock(ticker)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# MULTI STOCK API
# =========================================================

@app.get("/predict-multiple")
async def predict_multiple(tickers: str):

    ticker_list = list(
        set(
            ticker.strip().upper()
            for ticker in tickers.split(",")
            if ticker.strip()
        )
    )

    results = []

    for ticker in ticker_list:

        try:

            result = analyze_stock(ticker)

            results.append({
                "ticker": result["ticker"],
                "prediction": result["prediction"],
                "signal": result["signal"],
                "confidence": result["confidence"],
                "current_price": result["current_price"]
            })

        except Exception as e:

            results.append({
                "ticker": ticker,
                "prediction": "ERROR",
                "signal": "N/A",
                "confidence": 0,
                "current_price": 0,
                "error": str(e)
            })

    results.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    return {
        "success": True,
        "data": results
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "AI Stock Predictor"
    }
