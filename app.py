
import streamlit as st
import requests
import json
import time
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# 설정
# ============================================================
st.set_page_config(
    page_title="Trade Signal",
    page_icon="📊",
    layout="wide",
)

APP_KEY    = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]
BASE_URL   = "https://openapi.koreainvestment.com:9443"

WATCHLIST = {
    "삼성전자":           "005930",
    "SK하이닉스":         "000660",
    "LS전기":             "010120",
    "LIG넥스원":          "079550",
    "한화에어로스페이스":  "012450",
    "현대차":             "005380",
    "현대로템":           "064350",
    "두산에너빌리티":      "034020",
}
WATCHLIST_YF = {k: v + ".KS" for k, v in WATCHLIST.items()}

# ============================================================
# KIS 공통
# ============================================================
@st.cache_data(ttl=600)
def get_access_token():
    res = requests.post(
        f"{BASE_URL}/oauth2/tokenP",
        headers={"Content-Type": "application/json"},
        json={"grant_type": "client_credentials",
              "appkey": APP_KEY, "appsecret": APP_SECRET},
    )
    return res.json()["access_token"]

def get_headers(tr_id, token):
    return {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
        "appkey":        APP_KEY,
        "appsecret":     APP_SECRET,
        "tr_id":         tr_id,
        "custtype":      "P",
    }

def safe_get(url, headers, params):
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if not res.text.strip():
            return None
        data = res.json()
        return data if data.get("rt_cd") == "0" else None
    except:
        return None

def get_last_biz():
    d = datetime.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")

# ============================================================
# 데이터 수집
# ============================================================
@st.cache_data(ttl=300)
def fetch_market(token):
    last_biz = get_last_biz()
    result = {}

    # 코스피200
    data = safe_get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price",
        get_headers("FHPUP02100000", token),
        {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": "0021"},
    )
    if data:
        out = data["output"]
        result["코스피200"] = {
            "현재가":    out.get("bstp_nmix_prpr",     "-"),
            "전일대비":  out.get("bstp_nmix_prdy_vrss", "-"),
            "등락률(%)": out.get("bstp_nmix_prdy_ctrt", "-"),
        }

    # yfinance 지수
    tickers = {
        "VIX": "^VIX", "SOX": "^SOX",
        "원/달러": "KRW=X", "미국채10Y": "^TNX",
        "WTI": "CL=F", "구리": "HG=F",
    }
    for name, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if hist.empty:
                continue
            close = hist["Close"].iloc[-1]
            prev  = hist["Close"].iloc[-2] if len(hist) > 1 else close
            result[name] = {
                "현재가":    round(float(close), 2),
                "등락률(%)": round(float((close - prev) / prev * 100), 2),
            }
        except:
            pass

    return result

@st.cache_data(ttl=300)
def fetch_stocks(token):
    result = {}
    for name, ticker in WATCHLIST.items():
        time.sleep(0.4)
        data = safe_get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            get_headers("FHKST01010100", token),
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
        )
        if not data:
            continue
        out = data.get("output", {})
        result[name] = {
            "현재가":       int(out.get("stck_prpr",  0)),
            "전일대비":     int(out.get("prdy_vrss",  0)),
            "등락률(%)":    float(out.get("prdy_ctrt", 0)),
            "거래량":       int(out.get("acml_vol",   0)),
            "시가":         int(out.get("stck_oprc",  0)),
            "고가":         int(out.get("stck_hgpr",  0)),
            "저가":         int(out.get("stck_lwpr",  0)),
            "PER":          float(out.get("per",       0)),
            "PBR":          float(out.get("pbr",       0)),
            "시가총액(억)": int(out.get("hts_avls",   0)),
        }
    return result

@st.cache_data(ttl=600)
def fetch_tech():
    result = {}
    for name, ticker in WATCHLIST_YF.items():
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if hist.empty or len(hist) < 30:
                continue
            close  = hist["Close"]
            volume = hist["Volume"]

            # RSI
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi   = float((100 - 100 / (1 + gain / loss.replace(0, np.nan))).iloc[-1])

            # MACD
            ema12  = close.ewm(span=12, adjust=False).mean()
            ema26  = close.ewm(span=26, adjust=False).mean()
            macd   = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            hist_v = float((macd - signal).iloc[-1])
            golden = macd.iloc[-1] > signal.iloc[-1]

            # 볼린저
            mid  = close.rolling(20).mean()
            std  = close.rolling(20).std()
            up   = mid + 2 * std
            dn   = mid - 2 * std
            pctb = float(((close - dn) / (up - dn) * 100).iloc[-1])
            bw   = float(((up - dn) / mid * 100).iloc[-1])
            cur  = float(close.iloc[-1])
            bb_pos = ("상단돌파" if cur > float(up.iloc[-1])
                      else "하단이탈" if cur < float(dn.iloc[-1]) else "밴드내")

            # MA
            ma_above = sum(1 for p in [5, 20, 60, 120]
                          if len(close) >= p and cur > float(close.rolling(p).mean().iloc[-1]))

            # 거래량비율
            vr = float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1] * 100)

            result[name] = {
                "RSI": round(rsi, 2), "Histogram": round(hist_v, 2),
                "골든크로스": golden, "%B": round(pctb, 2),
                "밴드폭(%)": round(bw, 2), "BB위치": bb_pos,
                "MA상승수": ma_above, "거래량비율(%)": round(vr, 1),
            }
        except:
            pass
    return result

def calc_signal(stock, tech):
    score = 0
    log   = []
    rsi   = tech.get("RSI", 50)
    if rsi <= 30:   score += 2; log.append(f"RSI 과매도({rsi}) +2")
    elif rsi <= 45: score += 1; log.append(f"RSI 저점권({rsi}) +1")
    elif rsi >= 70: score -= 2; log.append(f"RSI 과매수({rsi}) -2")
    elif rsi >= 60: score -= 1; log.append(f"RSI 고점권({rsi}) -1")

    hist_v = tech.get("Histogram", 0)
    golden = tech.get("골든크로스", False)
    if golden:
        v = 2 if hist_v > 0 else 1; score += v; log.append(f"MACD 골든({hist_v:.0f}) +{v}")
    else:
        v = 2 if hist_v < 0 else 1; score -= v; log.append(f"MACD 데드({hist_v:.0f}) -{v}")

    pctb   = tech.get("%B", 50)
    bb_pos = tech.get("BB위치", "밴드내")
    if bb_pos == "하단이탈":   score += 2; log.append(f"BB 하단이탈 +2")
    elif pctb <= 20:            score += 1; log.append(f"BB 하단근접 +1")
    elif bb_pos == "상단돌파":  score -= 2; log.append(f"BB 상단돌파 -2")
    elif pctb >= 80:            score -= 1; log.append(f"BB 상단근접 -1")

    ma = tech.get("MA상승수", 0)
    if ma >= 3:   score += 2; log.append(f"MA 상승배열({ma}/4) +2")
    elif ma >= 2: score += 1; log.append(f"MA 부분상승({ma}/4) +1")
    elif ma <= 1: score -= 2; log.append(f"MA 하락배열({ma}/4) -2")
    else:         score -= 1; log.append(f"MA 부분하락({ma}/4) -1")

    vr = tech.get("거래량비율(%)", 100)
    if vr >= 200:  score += 1; log.append(f"거래량 급등({vr}%) +1")
    elif vr <= 50: score -= 1; log.append(f"거래량 급감({vr}%) -1")

    pbr = stock.get("PBR", 0)
    if 0 < pbr <= 1.0:  score += 1; log.append(f"PBR 저평가({pbr}) +1")
    elif pbr >= 15:     score -= 1; log.append(f"PBR 고평가({pbr}) -1")

    if score >= 5:   sig = "🟢 매수"
    elif score >= 2: sig = "🔵 관심"
    elif score >= -1: sig = "⚪ 관망"
    elif score >= -4: sig = "🟡 주의"
    else:             sig = "🔴 매도"

    return {"점수": score, "시그널": sig, "근거": log}

# ============================================================
# UI
# ============================================================
st.title("📊 Trade Signal")
st.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

token      = get_access_token()
market     = fetch_market(token)
stocks     = fetch_stocks(token)
tech_all   = fetch_tech()

# ------------------------------------------------------------
# 섹션 1. 시장 지표
# ------------------------------------------------------------
st.subheader("🌐 시장 지표")
cols = st.columns(4)
market_keys = ["코스피200", "VIX", "SOX", "원/달러"]
for i, key in enumerate(market_keys):
    d = market.get(key, {})
    val = d.get("현재가", "-")
    chg = d.get("등락률(%)", 0)
    try:
        color = "normal" if float(chg) == 0 else ("inverse" if key == "VIX" else "normal")
        cols[i].metric(key, val, f"{float(chg):+.2f}%", delta_color=color)
    except:
        cols[i].metric(key, val)

cols2 = st.columns(4)
for i, key in enumerate(["미국채10Y", "WTI", "구리", "코스피200"]):
    d = market.get(key, {})
    val = d.get("현재가", "-")
    chg = d.get("등락률(%)", 0)
    try:
        cols2[i].metric(key, val, f"{float(chg):+.2f}%")
    except:
        cols2[i].metric(key, val)

st.divider()

# ------------------------------------------------------------
# 섹션 2. 시그널 요약
# ------------------------------------------------------------
st.subheader("📋 시그널 요약")

rows = []
for name in WATCHLIST:
    s = stocks.get(name, {})
    t = tech_all.get(name, {})
    if not s or not t:
        continue
    sig = calc_signal(s, t)
    rows.append({
        "종목":       name,
        "현재가":     f"{s['현재가']:,}",
        "등락률(%)":  f"{s['등락률(%)']:+.2f}%",
        "RSI":        t.get("RSI", "-"),
        "%B":         t.get("%B", "-"),
        "거래량비율": f"{t.get('거래량비율(%)', '-')}%",
        "점수":       sig["점수"],
        "시그널":     sig["시그널"],
    })

df = pd.DataFrame(rows).sort_values("점수", ascending=False).reset_index(drop=True)
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ------------------------------------------------------------
# 섹션 3. 종목별 상세
# ------------------------------------------------------------
st.subheader("🔍 종목별 상세")
selected = st.selectbox("종목 선택", list(WATCHLIST.keys()))

s = stocks.get(selected, {})
t = tech_all.get(selected, {})

if s and t:
    sig = calc_signal(s, t)
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{s['현재가']:,}원", f"{s['등락률(%)']:+.2f}%")
    c2.metric("시그널", sig["시그널"], f"점수: {sig['점수']:+d}")
    c3.metric("거래량", f"{s['거래량']:,}")

    c4, c5, c6, c7 = st.columns(4)
    c4.metric("RSI(14)", t.get("RSI", "-"))
    c5.metric("%B",      t.get("%B",  "-"))
    c6.metric("밴드폭",  f"{t.get('밴드폭(%)', '-')}%")
    c7.metric("거래량비율", f"{t.get('거래량비율(%)', '-')}%")

    c8, c9, c10 = st.columns(3)
    c8.metric("PER",  s.get("PER",  "-"))
    c9.metric("PBR",  s.get("PBR",  "-"))
    c10.metric("시총", f"{s.get('시가총액(억)', 0):,}억")

    st.markdown("**판단 근거**")
    for r in sig["근거"]:
        st.markdown(f"- {r}")

st.divider()
st.caption("※ 본 앱은 투자 참고용이며, 투자 결정의 책임은 본인에게 있습니다.")
