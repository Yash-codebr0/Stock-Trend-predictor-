from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import warnings
warnings.filterwarnings("ignore")


# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(
    title="AI Stock Predictor API",
    description="Machine Learning based stock trend prediction API",
    version="1.0.0"
)


# =========================================================
# Request Models
# =========================================================

class StockRequest(BaseModel):
    ticker: str


class MultiStockRequest(BaseModel):
    tickers: list[str]


# =========================================================
# Data Fetch
# =========================================================

def get_data(ticker: str):

    try:
        df = yf.download(
            ticker,
            period="1y",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return None

        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.dropna(inplace=True)

        return df

    except Exception:
        return None


# =========================================================
# Feature Engineering
# =========================================================

def add_features(df):

    df = df.copy()

    # Returns
    df["Return"] = df["Close"].pct_change()

    # Moving averages
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA10"] = df["Close"].rolling(10).mean()

    # Volatility
    df["Volatility"] = df["Return"].rolling(5).std()

    # RSI
    delta = df["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (100 / (1 + rs))

    # Target
    df["Target"] = np.where(
        df["Close"].shift(-1) > df["Close"],
        1,
        0
    )

    df.dropna(inplace=True)

    return df


# =========================================================
# ML Model
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

    # Remove final target if necessary
    X_train = X.iloc[:-1]
    y_train = y.iloc[:-1]

    X_predict = X.iloc[[-1]]

    # Scaling
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)

    X_predict_scaled = scaler.transform(X_predict)

    # Model
    model = LogisticRegression(
        max_iter=1000
    )

    model.fit(
        X_train_scaled,
        y_train
    )

    # Prediction
    prediction = model.predict(
        X_predict_scaled
    )[0]

    probabilities = model.predict_proba(
        X_predict_scaled
    )[0]

    probability = probabilities[prediction]

    return int(prediction), float(probability)


# =========================================================
# Single Stock Prediction
# =========================================================

@app.get("/")
def home():

    return {
        "message": "AI Stock Predictor API",
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


@app.post("/predict")
def predict_stock(request: StockRequest):

    ticker = request.ticker.upper().strip()

    # Fetch data
    df = get_data(ticker)

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {ticker}"
        )

    # Features
    df = add_features(df)

    if len(df) < 50:
        raise HTTPException(
            status_code=400,
            detail="Not enough historical data"
        )

    try:

        prediction, probability = train_and_predict(df)

        trend = "UP" if prediction == 1 else "DOWN"

        return {
            "ticker": ticker,
            "prediction": trend,
            "confidence": round(probability * 100, 2)
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# Multi Stock Prediction
# =========================================================

@app.post("/predict/multiple")
def predict_multiple(request: MultiStockRequest):

    results = []

    # Remove duplicates
    tickers = list(
        set(
            ticker.upper().strip()
            for ticker in request.tickers
        )
    )

    for ticker in tickers:

        try:

            df = get_data(ticker)

            if df is None or df.empty:
                continue

            df = add_features(df)

            if len(df) < 50:
                continue

            prediction, probability = train_and_predict(df)

            results.append({
                "ticker": ticker,
                "prediction": (
                    "UP"
                    if prediction == 1
                    else "DOWN"
                ),
                "confidence": round(
                    probability * 100,
                    2
                )
            })

        except Exception as e:

            print(
                f"Skipping {ticker}: {e}"
            )

            continue

    # Sort by confidence
    results.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    return {
        "count": len(results),
        "results": results
    }