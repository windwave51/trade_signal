import streamlit as st
import requests
import time
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title='Trade Signal', page_icon='📊', layout='wide')

st.markdown('''<style>
.card{background:#ffffff;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #e0e4ec;box-shadow:0 2px 8px rgba(0,0,0,0.06);}
.stock-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #e8ecf0;}
.stock-name{font-size:1.1rem;font-weight:700;color:#1a1f2e;}
.stock-price{font-size:1.4rem;font-weight:800;color:#1a1f2e;}
.price-up{color:#e03131;}
.price-down{color:#1971c2;}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.85rem;font-weight:600;}
.badge-buy{background:#ebfbee;color:#2f9e44;border:1px solid #8ce99a;}
.badge-watch{background:#e7f5ff;color:#1971c2;border:1px solid #74c0fc;}
.badge-hold{background:#f8f9fa;color:#868e96;border:1px solid #ced4da;}
.badge-caution{background:#fff9db;color:#e67700;border:1px solid #ffd43b;}
.badge-sell{background:#fff5f5;color:#e03131;border:1px solid #ffa8a8;}
.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;}
.metric-item{background:#f8f9fc;border-radius:8px;padding:10px 12px;border:1px solid #e8ecf0;}
.metric-label{font-size:0.7rem;color:#868e96;margin-bottom:2px;text-transform:uppercase;letter-spacing:0.5px;}
.metric-value{font-size:0.95rem;font-weight:600;color:#1a1f2e;}
.reason-item{font-size:0.8rem;color:#495057;padding:3px 0;border-bottom:1px solid #e8ecf0;}
.tip{font-size:0.75rem;color:#adb5bd;font-style:italic;margin-top:2px;}
.divider{border:none;border-top:1px solid #e8ecf0;margin:8px 0;}
.market-card{background:#ffffff;border-radius:10px;padding:14px 16px;border:1px solid #e0e4ec;box-shadow:0 2px 6px rgba(0,0,0,0.05);text-align:center;}
.market-label{font-size:0.72rem;color:#868e96;margin-bottom:4px;}
.market-value{font-size:1.05rem;font-weight:700;color:#1a1f2e;}
.market-chg-up{font-size:0.8rem;color:#e03131;}
.market-chg-down{font-size:0.8rem;color:#1971c2;}
.indicator-table{width:100%;border-collapse:collapse;margin-top:8px;font-size:0.85rem;}
.indicator-table th{background:#f1f3f5;color:#495057;padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid #dee2e6;}
.indicator-table td{padding:8px 12px;border-bottom:1px solid #e8ecf0;color:#495057;vertical-align:top;}
.indicator-table td:first-child{font-weight:600;color:#1a1f2e;white-space:nowrap;width:100px;}
.indicator-table tr:last-child td{border-bottom:none;}
.indicator-table tr:hover td{background:#f8f9fc;}
</style>''', unsafe_allow_html=True)

APP_KEY    = st.secrets['APP_KEY']
APP_SECRET = st.secrets['APP_SECRET']
BASE_URL   = 'https://openapi.koreainvestment.com:9443'
KST        = pytz.timezone('Asia/Seoul')

WATCHLIST = {
    '삼성전자':           '005930',
    'SK하이닉스':         '000660',
    'LS전기':             '010120',
    'LIG넥스원':          '079550',
    '한화에어로스페이스':  '012450',
    '현대차':             '005380',
    '현대로템':           '064350',
    '두산에너빌리티':      '034020',
    'SK스퀘어':         '402340',
    '미래에셋증권':      '006800',
    '현대모비스':        '012330',
    '에스피지':          '058610',
}
WATCHLIST_YF = {k: v + '.KS' for k, v in WATCHLIST.items()}

INDICATOR_DESC = {
    'RSI':    '14일 상대강도지수. 70↑ 과매수(하락 가능), 30↓ 과매도(반등 가능)',
    'MACD':   '단기(12일)·장기(26일) 이동평균 차이. 골든크로스면 상승 모멘텀',
    '%B':     '볼린저밴드 내 현재 위치. 100%↑ 상단돌파(과열), 0%↓ 하단이탈(과매도)',
    '밴드폭': '볼린저밴드 폭. 좁을수록 변동성 수축(큰 움직임 예고)',
    'MA배열': '현재가가 5·20·60·120일 이평선 위에 있는 개수. 4/4 완전 상승배열',
    '거래량':  '20일 평균 거래량 대비 비율. 200%↑ 급등 신호, 50%↓ 관심 감소',
    'PER':    '주가수익비율. 낮을수록 이익 대비 저평가',
    'PBR':    '주가순자산비율. 1.0 이하면 자산 대비 저평가',
    '점수':      '6개 지표 합산. +5↑ 매수, +2~+4 관심, -1~+1 관망, -4~-2 주의, -5↓ 매도',
    '외국인순매수': '당일 외국인 순매수 주수·금액. 양수=순매수(강세), 음수=순매도(약세)',
    '기관순매수':   '당일 기관 순매수. 연기금·투신·은행 등 포함. 외국인과 방향 일치 시 강한 신호',
    '프로그램':     '컴퓨터 자동매매. 차익거래(선물-현물 가격차 이용)·비차익(ETF 리밸런싱 등) 포함',
}

@st.cache_data(ttl=1800)
def get_access_token():
    for attempt in range(3):
        try:
            res = requests.post(
                f'{BASE_URL}/oauth2/tokenP',
                headers={'Content-Type': 'application/json'},
                json={
                    'grant_type': 'client_credentials',
                    'appkey':     APP_KEY,
                    'appsecret':  APP_SECRET,
                },
                timeout=10,
            )
            data = res.json()
            if 'access_token' in data:
                return data['access_token']
            time.sleep(2)
        except Exception:
            time.sleep(2)
    st.error('KIS API 토큰 발급 실패. 잠시 후 새로고침해 주세요.')
    st.stop()

def get_headers(tr_id, token):
    return {
        'Content-Type':  'application/json',
        'Authorization': f'Bearer {token}',
        'appkey':        APP_KEY,
        'appsecret':     APP_SECRET,
        'tr_id':         tr_id,
        'custtype':      'P',
    }

def safe_get(url, headers, params):
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if not res.text.strip(): return None
        data = res.json()
        return data if data.get('rt_cd') == '0' else None
    except: return None

def safe_int(val, default=0):
    try: return int(val) if str(val).strip() not in ('', '-', 'None') else default
    except: return default

def safe_float(val, default=0.0):
    try: return float(val) if str(val).strip() not in ('', '-', 'None') else default
    except: return default

def get_last_biz():
    d = datetime.now(KST)
    while d.weekday() >= 5: d -= timedelta(days=1)
    return d.strftime('%Y%m%d')

def get_last_n_biz(n=5):
    days = []
    d = datetime.today()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
    return days[-1], days[0]

@st.cache_data(ttl=300)
def fetch_market(token):
    result = {}
    data = safe_get(
        f'{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price',
        get_headers('FHPUP02100000', token),
        {'FID_COND_MRKT_DIV_CODE': 'U', 'FID_INPUT_ISCD': '0021'},
    )
    if data:
        out = data['output']
        result['코스피200'] = {
            '현재가':    out.get('bstp_nmix_prpr', '-'),
            '등락률(%)': float(out.get('bstp_nmix_prdy_ctrt', 0)),
        }
    tickers = {'VIX':'^VIX','SOX':'^SOX','원/달러':'KRW=X','미국채10Y':'^TNX','WTI':'CL=F'}
    for name, ticker in tickers.items():
        try:
            hist = yf.Ticker(ticker).history(period='2d')
            if hist.empty: continue
            close = hist['Close'].iloc[-1]
            prev  = hist['Close'].iloc[-2] if len(hist) > 1 else close
            result[name] = {'현재가': round(float(close),2), '등락률(%)': round(float((close-prev)/prev*100),2)}
        except: pass
    return result

@st.cache_data(ttl=300)
def fetch_stocks(token):
    result = {}
    for name, ticker in WATCHLIST.items():
        time.sleep(0.4)
        data = safe_get(
            f'{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price',
            get_headers('FHKST01010100', token),
            {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': ticker},
        )
        if not data: continue
        out = data.get('output', {})
        # 프로그램 매매
        time.sleep(0.3)
        prog_data = safe_get(
            f'{BASE_URL}/uapi/domestic-stock/v1/quotations/program-trade-by-stock',
            get_headers('FHPPG04650100', token),
            {'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':ticker,
             'FID_INPUT_DATE_1':get_last_biz(),'FID_INPUT_DATE_2':get_last_biz(),
             'FID_PRC_CLS_CODE':'0','FID_PERIOD_DIV_CODE':'D'},
        )
        prog_out = prog_data['output'][0] if prog_data and prog_data.get('output') else {}

        # 외국인·기관·개인 수급
        time.sleep(0.3)
        start_5d, end_5d = get_last_n_biz(5)
        inv_data = safe_get(
            f'{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor',
            get_headers('FHKST01010900', token),
            {'FID_COND_MRKT_DIV_CODE':'J','FID_INPUT_ISCD':ticker,
             'FID_INPUT_DATE_1':start_5d,'FID_INPUT_DATE_2':end_5d,
             'FID_PERIOD_DIV_CODE':'D'},
        )
        inv_rows = inv_data['output'][:5] if inv_data and inv_data.get('output') else []
        inv_out  = inv_rows[0] if inv_rows else {}
        frgn_5d = sum(safe_int(r.get('frgn_ntby_tr_pbmn')) for r in inv_rows)
        orgn_5d = sum(safe_int(r.get('orgn_ntby_tr_pbmn')) for r in inv_rows)

        result[name] = {
            '현재가':       safe_int(out.get('stck_prpr')),
            '전일대비':     safe_int(out.get('prdy_vrss')),
            '등락률(%)':    safe_float(out.get('prdy_ctrt')),
            '거래량':       safe_int(out.get('acml_vol')),
            '시가':         safe_int(out.get('stck_oprc')),
            '고가':         safe_int(out.get('stck_hgpr')),
            '저가':         safe_int(out.get('stck_lwpr')),
            '52주고가':     safe_int(out.get('w52_hgpr')),
            '52주저가':     safe_int(out.get('w52_lwpr')),
            'PER':          safe_float(out.get('per')),
            'PBR':          safe_float(out.get('pbr')),
            '시가총액(억)': safe_int(out.get('hts_avls')),
            # 프로그램 매매
            '프로그램_순매수':  safe_int(prog_out.get('whol_smtn_ntby_qty')),
            '프로그램_매수량':  safe_int(prog_out.get('whol_smtn_shnu_vol')),
            '프로그램_매도량':  safe_int(prog_out.get('whol_smtn_seln_vol')),
            # 외국인·기관·개인
            '외국인_순매수':    safe_int(inv_out.get('frgn_ntby_qty')),
            '기관_순매수':      safe_int(inv_out.get('orgn_ntby_qty')),
            '개인_순매수':      safe_int(inv_out.get('prsn_ntby_qty')),
            '외국인_순매수금':    safe_int(inv_out.get('frgn_ntby_tr_pbmn')),
            '기관_순매수금':      safe_int(inv_out.get('orgn_ntby_tr_pbmn')),
            '외국인_5일순매수금': frgn_5d,
            '기관_5일순매수금':   orgn_5d,
            '기관_순매수금':    safe_int(inv_out.get('orgn_ntby_tr_pbmn')),
        }
    return result

@st.cache_data(ttl=600)
def fetch_tech():
    result = {}
    for name, ticker in WATCHLIST_YF.items():
        try:
            hist = yf.Ticker(ticker).history(period='6mo')
            if hist.empty or len(hist) < 30: continue
            close  = hist['Close']
            volume = hist['Volume']
            delta  = close.diff()
            gain   = delta.clip(lower=0).rolling(14).mean()
            loss   = (-delta.clip(upper=0)).rolling(14).mean()
            rsi    = float((100 - 100/(1+gain/loss.replace(0,np.nan))).iloc[-1])
            ema12  = close.ewm(span=12,adjust=False).mean()
            ema26  = close.ewm(span=26,adjust=False).mean()
            macd   = ema12 - ema26
            signal = macd.ewm(span=9,adjust=False).mean()
            hist_v = float((macd-signal).iloc[-1])
            golden = bool(macd.iloc[-1] > signal.iloc[-1])
            mid    = close.rolling(20).mean()
            std    = close.rolling(20).std()
            up     = mid + 2*std
            dn     = mid - 2*std
            pctb   = float(((close-dn)/(up-dn)*100).iloc[-1])
            bw     = float(((up-dn)/mid*100).iloc[-1])
            cur    = float(close.iloc[-1])
            bb_pos = '상단돌파' if cur>float(up.iloc[-1]) else '하단이탈' if cur<float(dn.iloc[-1]) else '밴드내'
            ma_above = sum(1 for p in [5,20,60,120] if len(close)>=p and cur>float(close.rolling(p).mean().iloc[-1]))
            vr = float(volume.iloc[-1]/volume.rolling(20).mean().iloc[-1]*100)
            result[name] = {
                'RSI':round(rsi,1),'Histogram':round(hist_v,1),
                '골든크로스':golden,'%B':round(pctb,1),
                '밴드폭(%)':round(bw,1),'BB위치':bb_pos,
                'MA상승수':ma_above,'거래량비율(%)':round(vr,1),
            }
        except: pass
    return result

def build_card(name, s, t):
    chg     = s.get('등락률(%)', 0)
    chg_cls = 'price-up' if chg > 0 else 'price-down'
    sign    = '▲' if chg > 0 else '▼'
    golden  = '✅ 골든' if t.get('골든크로스') else '❌ 데드'
    bb_pos  = t.get('BB위치', '-')
    return (
        '<div class="card">'
        '<div class="stock-header">'
        '<div>'
        '<div class="stock-name">' + name + '</div>'
            '</div>'
        '<div style="text-align:right">'
        '<div class="stock-price">' + f"{s['현재가']:,}" + '</div>'
        '<div class="' + chg_cls + '">' + sign + ' ' + f'{abs(chg):.2f}%' + '</div>'
        '</div></div>'
        '<div class="metric-grid">'
        '<div class="metric-item"><div class="metric-label">RSI(14)</div><div class="metric-value">' + str(t.get('RSI','-')) + '</div><div class="tip">70↑과매수 · 30↓과매도</div></div>'
        '<div class="metric-item"><div class="metric-label">MACD</div><div class="metric-value">' + golden + '</div><div class="tip">단기-장기 이평 교차</div></div>'
        '<div class="metric-item"><div class="metric-label">%B / 밴드위치</div><div class="metric-value">' + str(t.get('%B','-')) + '%</div><div class="tip">' + bb_pos + ' · 밴드폭' + str(t.get('밴드폭(%)','- ')) + '%</div></div>'
        '<div class="metric-item"><div class="metric-label">MA 배열</div><div class="metric-value">' + str(t.get('MA상승수',0)) + '/4</div><div class="tip">5·20·60·120일선 위</div></div>'
        '<div class="metric-item"><div class="metric-label">거래량비율</div><div class="metric-value">' + str(t.get('거래량비율(%)' ,'-')) + '%</div><div class="tip">20일 평균 대비</div></div>'
        '<div class="metric-item"><div class="metric-label">PER / PBR</div><div class="metric-value">' + str(s.get('PER','-')) + ' / ' + str(s.get('PBR','-')) + '</div><div class="tip">PBR 1↓ 자산 저평가</div></div>'
        '</div>'
        '<div style="margin-top:8px"><div class="metric-label" style="margin-bottom:4px">시가 / 고가 / 저가</div>'
        '<div style="font-size:0.8rem;color:#adb5bd;">' + f"{s.get('시가',0):,}" + ' / ' + f"{s.get('고가',0):,}" + ' / ' + f"{s.get('저가',0):,}" + '</div></div>'
        '<hr class="divider">'
        '<div class="metric-label" style="margin-bottom:6px">수급 동향</div>'
        '<div class="metric-grid">'
        '<div class="metric-item">'
        '<div class="metric-label">외국인 순매수</div>'
        '<div class="metric-value ' + ('price-up' if s.get('외국인_순매수',0)>0 else 'price-down') + '">'
        + ('+' if s.get('외국인_순매수',0)>0 else '') + f"{s.get('외국인_순매수',0):,}주" + '</div>'
        '<div class="tip">' + ('+' if s.get('외국인_순매수금',0)>0 else '') + f"{s.get('외국인_순매수금',0):,}백만" + '</div>'
        '</div>'
        '<div class="metric-item">'
        '<div class="metric-label">기관 순매수</div>'
        '<div class="metric-value ' + ('price-up' if s.get('기관_순매수',0)>0 else 'price-down') + '">'
        + ('+' if s.get('기관_순매수',0)>0 else '') + f"{s.get('기관_순매수',0):,}주" + '</div>'
        '<div class="tip">' + ('+' if s.get('기관_순매수금',0)>0 else '') + f"{s.get('기관_순매수금',0):,}백만" + '</div>'
        '</div>'
        '<div class="metric-item">'
        '<div class="metric-label">프로그램 순매수</div>'
        '<div class="metric-value ' + ('price-up' if s.get('프로그램_순매수',0)>0 else 'price-down') + '">'
        + ('+' if s.get('프로그램_순매수',0)>0 else '') + f"{s.get('프로그램_순매수',0):,}주" + '</div>'
        '<div class="tip">매수 ' + f"{s.get('프로그램_매수량',0):,}" + ' / 매도 ' + f"{s.get('프로그램_매도량',0):,}" + '</div>'
        '</div>'
        '</div>'
        '</div>'
    )

st.title('📊 Trade Signal')
st.caption(f"마지막 업데이트: {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}  |  ※ 투자 참고용")

token    = get_access_token()
market   = fetch_market(token)
stocks   = fetch_stocks(token)
tech_all = fetch_tech()

st.subheader('🌐 시장 지표')
market_items = [
    ('코스피200', '국내 대형주 200개 지수'),
    ('VIX',      '공포지수. 20↑ 불안, 30↑ 공포'),
    ('SOX',      '미국 반도체지수. 국내 반도체주 선행'),
    ('원/달러',  '환율↑ = 수출주 유리'),
    ('미국채10Y','장기금리↑ = 성장주 부담'),
    ('WTI',      '국제유가. 에너지·운송 업종 영향'),
]
mcols = st.columns(len(market_items))
for i, (key, desc) in enumerate(market_items):
    d   = market.get(key, {})
    val = d.get('현재가', '-')
    chg = d.get('등락률(%)', 0)
    try:
        chg_f   = float(chg)
        chg_str = f'{chg_f:+.2f}%'
        chg_cls = 'market-chg-up' if chg_f > 0 else 'market-chg-down'
    except:
        chg_str = '-'; chg_cls = 'market-chg-down'
    mcols[i].markdown(
        '<div class="market-card">'
        '<div class="market-label">' + key + '</div>'
        '<div class="market-value">' + str(val) + '</div>'
        '<div class="' + chg_cls + '">' + chg_str + '</div>'
        '<div class="tip">' + desc + '</div>'
        '</div>', unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)
st.subheader('📋 시그널 요약')
rows = []
for name in WATCHLIST:
    s = stocks.get(name, {}); t = tech_all.get(name, {})
    if not s or not t: continue
    rows.append({
        '종목': name,
        '현재가(원)': f"{s['현재가']:,}",
        '등락률': f"{s['등락률(%)']:+.2f}%",
        'RSI': t.get('RSI','-'),
        '%B': t.get('%B','-'),
        'MA배열': f"{t.get('MA상승수',0)}/4",
        '거래량비율': f"{t.get('거래량비율(%)' ,'-')}%",
    })
import pandas as pd
df = pd.DataFrame(rows).reset_index(drop=True)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown('<br>', unsafe_allow_html=True)
st.subheader('🔍 종목별 상세')
names = list(WATCHLIST.keys())
for row_start in range(0, len(names), 3):
    cols = st.columns(3)
    for col_idx, name in enumerate(names[row_start:row_start+3]):
        s = stocks.get(name, {}); t = tech_all.get(name, {})
        if not s or not t: continue
        with cols[col_idx]:
            st.markdown(build_card(name, s, t,), unsafe_allow_html=True)

st.subheader('📚 지표 설명')
rows_desc = [{'지표': k, '설명': v} for k, v in INDICATOR_DESC.items()]
table_html = '<table class="indicator-table"><thead><tr><th>지표</th><th>설명</th></tr></thead><tbody>'
for r in rows_desc:
    table_html += '<tr><td>' + r['지표'] + '</td><td>' + r['설명'] + '</td></tr>'
table_html += '</tbody></table>'
st.markdown(table_html, unsafe_allow_html=True)

st.caption('※ 본 앱은 투자 참고용이며, 투자 결정의 책임은 본인에게 있습니다.')
