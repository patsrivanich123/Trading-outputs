"""Technical levels. Migrated from the scheduled brief's make_brief.py. Pure functions, no plotting."""
import numpy as np, pandas as pd

def rsi(s: pd.Series, n=14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def swing_levels(c: pd.Series, px: float, atr: float, k=3, lookback=90):
    s = c.iloc[-lookback:]
    highs, lows = [], []
    for i in range(k, len(s) - k):
        w = s.iloc[i-k:i+k+1]
        if s.iloc[i] == w.max(): highs.append(float(s.iloc[i]))
        if s.iloc[i] == w.min(): lows.append(float(s.iloc[i]))
    merged = []
    for v in sorted(set(highs + lows)):
        if merged and abs(v - merged[-1]) < 0.6 * atr: merged[-1] = (merged[-1] + v) / 2
        else: merged.append(v)
    res = sorted([v for v in merged if v > px + 0.3 * atr])[:2]
    sup = sorted([v for v in merged if v < px - 0.3 * atr], reverse=True)[:2]
    return res, sup

def analyse(name: str, kind: str, close: pd.Series, high: pd.Series | None = None, low: pd.Series | None = None) -> dict:
    c = close.astype(float); px = float(c.iloc[-1]); prev = float(c.iloc[-2])
    out = dict(name=name, kind=kind, last=px, chg=px - prev, chg_pct=(px / prev - 1) * 100, asof=str(c.index[-1]),
               chg_1w_pct=(px / float(c.iloc[-6]) - 1) * 100 if len(c) > 6 else None,
               chg_1m_pct=(px / float(c.iloc[-22]) - 1) * 100 if len(c) > 22 else None,
               hi_6m=float(c.max()), lo_6m=float(c.min()))
    if kind != "ta": return out
    ma = {n: float(c.rolling(n).mean().iloc[-1]) for n in (20, 50, 100) if len(c) >= n}
    bb_m, bb_s = c.rolling(20).mean(), c.rolling(20).std()
    if high is not None and low is not None and len(high) >= 15:
        h, l = high.astype(float), low.astype(float); cc = c.reindex(h.index)
        tr = pd.concat([h - l, (h - cc.shift()).abs(), (l - cc.shift()).abs()], axis=1).max(axis=1).dropna()
        atr = float(tr.iloc[-14:].mean()); ph, pl = float(h.iloc[-1]), float(l.iloc[-1])
    else:
        atr = float(c.diff().abs().iloc[-14:].mean()); ph = pl = px
    P = (ph + pl + px) / 3
    piv = dict(R2=P + (ph - pl), R1=2*P - pl, P=P, S1=2*P - ph, S2=P - (ph - pl))
    res, sup = swing_levels(c, px, atr, lookback=min(120, len(c)))
    if len(res) < 2 and c.iloc[-60:].max() > px: res = sorted(set(res + [float(c.iloc[-60:].max())]))[:2]
    if len(sup) < 2 and c.iloc[-60:].min() < px: sup = sorted(set(sup + [float(c.iloc[-60:].min())]), reverse=True)[:2]
    trend = ("up" if px > ma.get(50, px) > ma.get(100, px) else "down" if px < ma.get(50, px) < ma.get(100, px) else "range/mixed")
    out.update(ma=ma, rsi14=float(rsi(c).iloc[-1]), atr14=atr, bb_up=float((bb_m + 2*bb_s).iloc[-1]),
               bb_dn=float((bb_m - 2*bb_s).iloc[-1]), pivots=piv, resistance=res, support=sup, trend=trend)
    return out
