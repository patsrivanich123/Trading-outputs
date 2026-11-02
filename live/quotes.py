#!/usr/bin/env python3
"""15-minute live price layer. Runs in GitHub Actions inside Trading-outputs (NOT in the Trading repo, NOT via Claude).
Pulls free delayed quotes (Yahoo Finance via yfinance), recomputes levels with ta.py, writes live/levels_live.json.
Reference levels remain the 06:37 IBKR run; this is for glancing + reload. ~15 min delayed, unofficial feed."""
import json, datetime as dt, warnings, sys, os
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd, yfinance as yf
import ta

ICT = dt.timezone(dt.timedelta(hours=7))
# registry name -> (yahoo symbol, kind, scale, dp, note)
SYMBOLS = [
    ("USDJPY",        "JPY=X",   "ta", 1.0, 2, "spot"),
    ("UST 10Y (%)",   "^TNX",    "ta", 0.1, 3, "CBOE TNX /10"),
    ("DXY (ICE fut)", "DX=F",    "ta", 1.0, 2, "continuous front"),
    ("Brent CO1",     "BZ=F",    "ta", 1.0, 2, "continuous front"),
    ("Bitcoin",       "BTC-USD", "ta", 1.0, 0, "spot"),
    ("S&P 500",       "^GSPC",   "eq", 1.0, 0, ""),
    ("Nasdaq 100",    "^NDX",    "eq", 1.0, 0, ""),
    ("KOSPI 200",     "^KS200",  "eq", 1.0, 2, ""),
    ("Hang Seng",     "^HSI",    "eq", 1.0, 0, ""),
]

def one(name, sym, kind, scale, dp, note):
    t = yf.Ticker(sym)
    d = t.history(period="8mo", interval="1d", auto_adjust=False)
    if d is None or len(d) < 30: raise RuntimeError("no daily history")
    d = d.dropna(subset=["Close"])
    c = (d["Close"] * scale); h = (d["High"] * scale); l = (d["Low"] * scale)
    c.index = pd.to_datetime(c.index).tz_localize(None).normalize(); h.index = c.index; l.index = c.index
    last, last_ts, src = float(c.iloc[-1]), c.index[-1].isoformat(), "daily close"
    try:
        i = t.history(period="2d", interval="15m")
        if i is not None and len(i):
            last = float(i["Close"].dropna().iloc[-1]) * scale; last_ts = pd.Timestamp(i.index[-1]).tz_convert("UTC").isoformat(); src = "15m bar"
    except Exception: pass
    # levels from daily closes, but with the live last swapped in
    c2 = c.copy(); c2.iloc[-1] = last
    lv = ta.analyse(name, kind, c2, h.iloc[-30:], l.iloc[-30:])
    prev_close = float(c.iloc[-2]) if last_ts[:10] > c.index[-1].strftime("%Y-%m-%d") or src == "daily close" else float(c.iloc[-2])
    lv.update(dict(last=round(last, 6), chg=last - prev_close, chg_pct=(last / prev_close - 1) * 100, prev_close=prev_close,
                   last_ts=last_ts, source=f"yahoo:{sym} ({src})", dp=dp, note=note))
    return lv

def main(out):
    res, errs = [], []
    for name, sym, kind, scale, dp, note in SYMBOLS:
        try: res.append(one(name, sym, kind, scale, dp, note))
        except Exception as e: errs.append(dict(name=name, symbol=sym, error=str(e)[:200]))
    now = dt.datetime.now(dt.timezone.utc)
    doc = dict(asof_utc=now.isoformat(timespec="minutes"), asof_ict=now.astimezone(ICT).strftime("%Y-%m-%d %H:%M"),
               source="Yahoo Finance via yfinance, ~15 min delayed, unofficial. Reference levels are the 06:37 IBKR run.",
               assets=res, errors=errs)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(doc, open(out, "w"), indent=1, default=float)
    print(f"live: {len(res)} ok, {len(errs)} failed, {doc['asof_ict']} ICT")
    for e in errs: print("  FAIL", e)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live/levels_live.json")
