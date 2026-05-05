# ============================================================
# scoring.py — 1단계 스코어링 + 2단계 해석 엔진
# ============================================================

SECTOR_MAP = {
    '삼성전자':           '전기·전자',
    'SK하이닉스':         '전기·전자',
    'LS전기':             '전력기기',
    'LIG넥스원':          '방산',
    '한화에어로스페이스':  '방산',
    '현대차':             '운수장비',
    '현대로템':           '방산·기계',
    '두산에너빌리티':      '에너지·플랜트',
}

STOCK_TYPES = {
    '삼성전자':           ['구조적 성장주', '사이클 업종주'],
    'SK하이닉스':         ['구조적 성장주', '사이클 업종주'],
    'LS전기':             ['정책·수주 모멘텀주', '구조적 성장주'],
    'LIG넥스원':          ['정책·수주 모멘텀주'],
    '한화에어로스페이스':  ['정책·수주 모멘텀주'],
    '현대차':             ['사이클 업종주', '저평가 가치주'],
    '현대로템':           ['정책·수주 모멘텀주'],
    '두산에너빌리티':      ['정책·수주 모멘텀주', '구조적 성장주'],
}

SOX_LINKED      = {'삼성전자', 'SK하이닉스'}
AI_POWER_LINKED = {'LS전기', '두산에너빌리티'}

PBR_BENCH = {
    '전기·전자':    {'low': 1.0, 'fair': 2.5, 'high': 5.0},
    '전력기기':     {'low': 1.5, 'fair': 3.5, 'high': 8.0},
    '방산':         {'low': 2.0, 'fair': 5.0, 'high': 12.0},
    '방산·기계':    {'low': 1.5, 'fair': 4.0, 'high': 10.0},
    '운수장비':     {'low': 0.5, 'fair': 1.2, 'high': 2.5},
    '에너지·플랜트':{'low': 0.8, 'fair': 2.0, 'high': 4.0},
}
PER_BENCH = {
    '전기·전자':    {'low': 10, 'fair': 20, 'high': 40},
    '전력기기':     {'low': 12, 'fair': 25, 'high': 60},
    '방산':         {'low': 15, 'fair': 30, 'high': 60},
    '방산·기계':    {'low': 12, 'fair': 25, 'high': 50},
    '운수장비':     {'low': 5,  'fair': 12, 'high': 25},
    '에너지·플랜트':{'low': 8,  'fair': 20, 'high': 50},
}
GROWTH_SCORE_OVERRIDE = {'현대차': 7, '현대로템': 8}
GROWTH_SCORE_BASE = {
    '전기·전자': 8, '전력기기': 9, '방산': 9,
    '방산·기계': 8, '운수장비': 5, '에너지·플랜트': 8,
}

def is_missing(val):
    return val is None or val == '' or val == '-'

def safe_float(val, default=0.0):
    try:
        return float(val) if not is_missing(val) else default
    except:
        return default

def pct_of_mktcap(amount_krw, mktcap_억):
    if not mktcap_억: return None
    return round(amount_krw / (mktcap_억 * 1e8) * 100, 4)

def pct_of_trading(amount_krw, trading_krw):
    if not trading_krw: return None
    return round(amount_krw / trading_krw * 100, 4)

def score_fundamental(s, t, name):
    sector     = SECTOR_MAP.get(name, '기타')
    pbr        = s.get('PBR')
    per        = s.get('PER')
    pbr_b      = PBR_BENCH.get(sector, {'low':1.0,'fair':2.5,'high':5.0})
    per_b      = PER_BENCH.get(sector, {'low':10,'fair':25,'high':50})
    w52h_pct   = s.get('52주고가대비(%)')
    ma_cnt     = t.get('MA상승수', 0)
    stock_type = STOCK_TYPES.get(name, [])
    g_score    = GROWTH_SCORE_OVERRIDE.get(name, GROWTH_SCORE_BASE.get(sector, 5))
    g_reason   = (f'{name} 종목별 성장성 조정값 ({g_score}점)' if name in GROWTH_SCORE_OVERRIDE
                  else f'{sector} 업종 성장성 기준 ({g_score}점)')
    if '정책·수주 모멘텀주' in stock_type: e_score,e_reason=7,'정책·수주 모멘텀주 — 수주잔고·정책 기반 가시성 양호'
    elif '구조적 성장주' in stock_type:    e_score,e_reason=7,'구조적 성장주 — 중장기 실적 성장 가시성 유효'
    elif '사이클 업종주' in stock_type:    e_score,e_reason=5,'사이클 업종주 — 업황 사이클 위치에 따라 편차 큼'
    else:                                   e_score,e_reason=4,'실적 추정치 데이터 없음 — 기본값'
    if '정책·수주 모멘텀주' in stock_type: m_score,m_reason=7,'정책·수주 모멘텀주 — 이벤트 모멘텀 유효'
    elif '구조적 성장주' in stock_type:    m_score,m_reason=6,'구조적 성장주 — 중장기 모멘텀 지속'
    else:                                   m_score,m_reason=4,'이벤트 데이터 없음 — 기본값'
    if is_missing(pbr) and is_missing(per):
        v_score,v_reason=2,'PBR·PER 데이터 없음'
    else:
        def classify_pbr(v):
            if is_missing(v): return None
            v=float(v)
            if v<pbr_b['low']: return '저평가'
            elif v<pbr_b['fair']: return '적정'
            elif v<pbr_b['high']: return '고평가'
            else: return '심각한 고평가'
        def classify_per(v):
            if is_missing(v): return None
            v=float(v)
            if v<=0: return '적자'
            elif v<per_b['low']: return '저평가'
            elif v<per_b['fair']: return '적정'
            elif v<per_b['high']: return '고평가'
            else: return '심각한 고평가'
        pbr_cls=classify_pbr(pbr); per_cls=classify_per(per)
        combined=[x for x in [pbr_cls,per_cls] if x]
        if all(x in ['저평가','적정'] for x in combined): v_score=5
        elif any(x=='저평가' for x in combined):          v_score=4
        elif all(x in ['적정','고평가'] for x in combined):v_score=3
        elif any(x=='심각한 고평가' for x in combined):   v_score=1
        elif any(x=='적자' for x in combined):             v_score=2
        else:                                               v_score=2
        v_reason=(f'PBR {pbr}({pbr_cls}) / PER {per}({per_cls})'
                  f' — 업종기준 PBR:{pbr_b["low"]}~{pbr_b["high"]}'
                  f' / PER:{per_b["low"]}~{per_b["high"]}')
    if is_missing(w52h_pct):
        r_score,r_reason=2,'52주 위치 데이터 없음'
    else:
        w52h=float(w52h_pct)
        if w52h>=-5:     pos_level,base='신고가 근접',1
        elif w52h>=-15:  pos_level,base='고점 근처',2
        elif w52h>=-30:  pos_level,base='조정 중',3
        elif w52h>=-50:  pos_level,base='깊은 조정',4
        else:            pos_level,base='장기 낙폭',5
        if base<=2 and ma_cnt>=3:   r_score=max(1,base-1); r_reason=f'52주 고가 대비 {w52h}%({pos_level}) + MA {ma_cnt}/4 — 추격 진입 위험'
        elif base>=4 and ma_cnt<=1: r_score=max(2,base-1); r_reason=f'52주 고가 대비 {w52h}%({pos_level}) + MA {ma_cnt}/4 — 하락추세 지속 주의'
        elif base>=3 and ma_cnt>=3: r_score=min(5,base+1); r_reason=f'52주 고가 대비 {w52h}%({pos_level}) + MA {ma_cnt}/4 — 눌림목 진입 후보'
        else:                       r_score=base;          r_reason=f'52주 고가 대비 {w52h}%({pos_level}) + MA {ma_cnt}/4'
    total=g_score+e_score+m_score+v_score+r_score
    return {'total':total,'max':40,'details':{
        'industry_growth':    {'score':g_score,'max':10,'reason':g_reason},
        'earnings_visibility':{'score':e_score,'max':10,'reason':e_reason},
        'event_momentum':     {'score':m_score,'max':10,'reason':m_reason},
        'valuation_burden':   {'score':v_score,'max':5, 'reason':v_reason},
        'risk_manageability': {'score':r_score,'max':5, 'reason':r_reason},
    }}

def score_flow(s):
    mktcap=s.get('시가총액(억)',0); trd_val=s.get('거래대금',0) or 0
    def pick_flow(key_5d,key_1d):
        v5=s.get(key_5d); v1=s.get(key_1d)
        if not is_missing(v5): return safe_float(v5)*1_000_000,'5일누적'
        if not is_missing(v1): return safe_float(v1)*1_000_000,'당일'
        return None,'없음'
    frgn_amt,frgn_src=pick_flow('외국인_5일순매수금','외국인_순매수금')
    orgn_amt,orgn_src=pick_flow('기관_5일순매수금','기관_순매수금')
    prog_raw=s.get('프로그램_순매수금')
    prog_amt=safe_float(prog_raw) if not is_missing(prog_raw) else None
    def calc_flow_score(amt,src,label,max_score):
        if amt is None: return 3,None,None,f'{label} 데이터 없음 ({src})'
        mktcap_pct=pct_of_mktcap(abs(amt),mktcap)
        trd_pct=pct_of_trading(abs(amt),trd_val) if trd_val else None
        trd_pct=min(trd_pct,99.0) if trd_pct else None
        direction=1 if amt>=0 else -1
        weight=1.2 if src=='5일누적' else 1.0
        thresh=[0.5,0.1] if label=='외국인' else [0.3,0.05]
        if mktcap_pct is not None:
            if mktcap_pct>=thresh[0]: base=9
            elif mktcap_pct>=thresh[1]: base=7
            else: base=5
        else: base=5
        if trd_pct is not None:
            if trd_pct>=5.0: base=min(max_score,base+1)
            elif trd_pct<=0.5: base=max(1,base-1)
        if direction<0: base=max(1,max_score-base)
        final=round(min(max_score,base*weight))
        reason=(f'{label} {"+" if amt>=0 else ""}{amt/1e6:.0f}백만원 ({src})'
               +(f' / 시총대비 {mktcap_pct:.3f}%' if mktcap_pct is not None else '')
               +(f' / 거래대금대비 {trd_pct:.2f}%' if trd_pct is not None else ''))
        return final,mktcap_pct,trd_pct,reason
    frgn_score,frgn_mktcap_pct,frgn_trd_pct,frgn_reason=calc_flow_score(frgn_amt,frgn_src,'외국인',10)
    orgn_score,orgn_mktcap_pct,orgn_trd_pct,orgn_reason=calc_flow_score(orgn_amt,orgn_src,'기관',10)
    frgn_dir=None if (frgn_amt is None or frgn_amt==0) else (1 if frgn_amt>0 else -1)
    orgn_dir=None if (orgn_amt is None or orgn_amt==0) else (1 if orgn_amt>0 else -1)
    prsn_d=s.get('개인_순매수') or 0
    prsn_dir=None if is_missing(prsn_d) else (1 if prsn_d>0 else -1)
    if frgn_dir is None or orgn_dir is None: align_score,align_reason=2,'수급 데이터 부족 — 방향 판단 보류'
    elif frgn_dir==1 and orgn_dir==1:        align_score,align_reason=5,'외국인·기관 동시 순매수 — 강한 수급 신호'
    elif frgn_dir==-1 and orgn_dir==-1:      align_score,align_reason=0,'외국인·기관 동시 순매도 — 강한 이탈 신호'
    else:                                     align_score,align_reason=2,'외국인·기관 방향 엇갈림 — 확인 필요'
    def calc_prog_driven_risk(p,t):
        if p is None or not t or t==0: return False
        return min(abs(p)/t*100,99.0)>15.0
    prog_driven_risk=calc_prog_driven_risk(prog_amt,trd_val)
    prog_score,prog_reason=2,'프로그램 데이터 없음'
    if prog_amt is not None:
        if trd_val:
            pp=min(pct_of_trading(abs(prog_amt),trd_val),99.0)
            if prog_amt>0 and pp>15:   prog_score,prog_reason=4,f'프로그램 거래대금대비 +{pp:.1f}% — ETF·바스켓 주도'
            elif prog_amt>0:            prog_score,prog_reason=3,f'프로그램 거래대금대비 +{pp:.1f}% 소량 순매수'
            elif pp>15:                 prog_score,prog_reason=1,f'프로그램 거래대금대비 -{pp:.1f}% — 바스켓 이탈 주도'
            else:                       prog_score,prog_reason=2,f'프로그램 거래대금대비 -{pp:.1f}% 소량 순매도'
        else:
            pm=pct_of_mktcap(abs(prog_amt),mktcap) or 0
            prog_score=3 if prog_amt>0 else 2
            prog_reason=f'프로그램 시총대비 {"+" if prog_amt>0 else ""}{pm:.3f}% (거래대금 없음)'
    total=frgn_score+orgn_score+align_score+prog_score
    metrics={'foreign_pct_mktcap':frgn_mktcap_pct,'foreign_pct_trading':frgn_trd_pct,
             'foreign_direction':frgn_dir,'foreign_source':frgn_src,
             'institution_pct_mktcap':orgn_mktcap_pct,'institution_pct_trading':orgn_trd_pct,
             'institution_direction':orgn_dir,'institution_source':orgn_src,
             'retail_direction':prsn_dir,'program_driven_risk':prog_driven_risk}
    return {'total':total,'max':30,'metrics':metrics,'details':{
        'foreign_cumulative':            {'score':frgn_score, 'max':10,'reason':frgn_reason},
        'institution_cumulative':        {'score':orgn_score, 'max':10,'reason':orgn_reason},
        'foreign_institution_alignment': {'score':align_score,'max':5, 'reason':align_reason},
        'program_trading':               {'score':prog_score, 'max':5, 'reason':prog_reason},
    }}

def score_technical(t):
    rsi=t.get('RSI',50); golden=t.get('골든크로스',False); hist_v=t.get('Histogram',0)
    pctb=t.get('%B',50); bw=t.get('밴드폭(%)',20); ma=t.get('MA상승수',0)
    vr=t.get('거래량비율(%)',100); bb_pos=t.get('BB위치','밴드내')
    ma_score={4:7,3:5,2:3,1:1,0:0}.get(ma,0)
    ma_reason={4:'4/4 완전 상승배열 — 추세 강하나 추격 주의',3:'3/4 상승배열 — 중기 추세 유지',
               2:'2/4 혼조 — 방향성 불명확',1:'1/4 약세배열',0:'0/4 하락배열'}.get(ma,'-')
    if rsi<=30:   rsi_score,rsi_reason=3,f'RSI {rsi} — 과매도. 하락추세 중 저점 단정 금지'
    elif rsi<=45: rsi_score,rsi_reason=4,f'RSI {rsi} — 눌림목 구간. 진입 검토 가능'
    elif rsi<=65: rsi_score,rsi_reason=5,f'RSI {rsi} — 안정적 상승 구간'
    elif rsi<=75: rsi_score,rsi_reason=3,f'RSI {rsi} — 상승 추세이나 과열 경계'
    elif rsi<=80: rsi_score,rsi_reason=2,f'RSI {rsi} — 과열. 신규 진입 비추'
    else:         rsi_score,rsi_reason=1,f'RSI {rsi} — 심각한 과열'
    if golden and hist_v>0:      macd_score,macd_reason=5,'골든크로스 + 히스토그램 양수 — 상승 모멘텀'
    elif golden and hist_v<=0:   macd_score,macd_reason=3,'골든크로스이나 히스토그램 수축 — 모멘텀 약화'
    elif not golden and hist_v>0:macd_score,macd_reason=2,'데드크로스이나 히스토그램 개선 — 전환 확인 필요'
    else:                        macd_score,macd_reason=1,'데드크로스 + 히스토그램 음수 — 하락 모멘텀'
    pctb_f=safe_float(pctb)
    if is_missing(pctb):        pctb_score,pctb_reason=2,'%B 데이터 없음'
    elif bb_pos=='하단이탈':     pctb_score,pctb_reason=3,f'%B {pctb} — 하단 이탈. 하락추세 가능'
    elif pctb_f<=20:             pctb_score,pctb_reason=5,f'%B {pctb} — 하단 근접. 반등 가능성'
    elif pctb_f<=50:             pctb_score,pctb_reason=4,f'%B {pctb} — 중립 하단. 안정적'
    elif pctb_f<=80:             pctb_score,pctb_reason=3,f'%B {pctb} — 중립 상단. 부담 확인'
    elif bb_pos=='상단돌파':     pctb_score,pctb_reason=2,f'%B {pctb} — 상단 돌파. 거래량 동반 여부 확인'
    else:                        pctb_score,pctb_reason=2,f'%B {pctb} — 상단 근접. 신규 진입 부담'
    bw_f=safe_float(bw)
    if is_missing(bw):   bw_score,bw_reason=1,'밴드폭 데이터 없음'
    elif bw_f<10:        bw_score,bw_reason=3,f'밴드폭 {bw}% — 수축. 방향성 이탈 임박 가능'
    elif bw_f<25:        bw_score,bw_reason=2,f'밴드폭 {bw}% — 보통'
    else:                bw_score,bw_reason=1,f'밴드폭 {bw}% — 확대. 변동성 큰 구간'
    vr_f=safe_float(vr)
    if is_missing(vr):   vr_score,vr_reason=2,'거래량 데이터 없음'
    elif vr_f>=200:      vr_score,vr_reason=4,f'거래량 {vr}% — 급증. 상승 시 유입/하락 시 이탈'
    elif vr_f>=130:      vr_score,vr_reason=4,f'거래량 {vr}% — 증가. 관심 유입'
    elif vr_f>=70:       vr_score,vr_reason=3,f'거래량 {vr}% — 보통'
    elif vr_f>=50:       vr_score,vr_reason=2,f'거래량 {vr}% — 감소. 관심 약화'
    else:                vr_score,vr_reason=1,f'거래량 {vr}% — 급감. 수급 공백'
    total=ma_score+rsi_score+macd_score+pctb_score+bw_score+vr_score
    return {'total':total,'max':30,'details':{
        'ma_alignment':{'score':ma_score,   'max':7,'reason':ma_reason},
        'rsi':         {'score':rsi_score,  'max':5,'reason':rsi_reason},
        'macd':        {'score':macd_score, 'max':5,'reason':macd_reason},
        'percent_b':   {'score':pctb_score, 'max':5,'reason':pctb_reason},
        'bandwidth':   {'score':bw_score,   'max':3,'reason':bw_reason},
        'volume':      {'score':vr_score,   'max':5,'reason':vr_reason},
    }}

def score_market_env(market, name):
    adj,notes=0,[]
    vix=safe_float(market.get('VIX',{}).get('현재가'))
    if vix:
        if vix>=30:   adj-=5; notes.append(f'VIX {vix:.1f} — 공포 구간 -5점')
        elif vix>=20: adj-=2; notes.append(f'VIX {vix:.1f} — 불안 구간 -2점')
        elif vix<=13: adj+=2; notes.append(f'VIX {vix:.1f} — 안정 구간 +2점')
    k200=safe_float(market.get('코스피200',{}).get('등락률(%)'))
    if k200:
        if k200<=-1.5:   adj-=3; notes.append(f'코스피200 {k200:+.2f}% 약세 -3점')
        elif k200<=-0.5: adj-=1; notes.append(f'코스피200 {k200:+.2f}% 소폭 하락 -1점')
        elif k200>=1.0:  adj+=2; notes.append(f'코스피200 {k200:+.2f}% 강세 +2점')
    krw=safe_float(market.get('원/달러',{}).get('등락률(%)'))
    if krw:
        if krw>=1.0:    adj-=2; notes.append(f'원달러 {krw:+.2f}% 원화 약세 -2점')
        elif krw<=-1.0: adj+=1; notes.append(f'원달러 {krw:+.2f}% 원화 강세 +1점')
    if name in SOX_LINKED:
        sox=safe_float(market.get('SOX',{}).get('등락률(%)'))
        if sox:
            if sox>=1.5:    adj+=2; notes.append(f'SOX {sox:+.2f}% 강세 — 반도체 +2점')
            elif sox<=-1.5: adj-=2; notes.append(f'SOX {sox:+.2f}% 약세 — 반도체 -2점')
            elif sox>=0.5:  adj+=1; notes.append(f'SOX {sox:+.2f}% 소폭 강세 +1점')
    if name in AI_POWER_LINKED:
        copper=safe_float(market.get('구리',{}).get('등락률(%)'))
        if copper:
            if copper>=1.0:    adj+=1; notes.append(f'구리 {copper:+.2f}% 강세 — AI전력 수요 +1점')
            elif copper<=-1.5: adj-=1; notes.append(f'구리 {copper:+.2f}% 약세 — AI전력 둔화 -1점')
        tnx=safe_float(market.get('미국채10Y',{}).get('등락률(%)'))
        if tnx:
            if tnx>=0.05:    adj-=1; notes.append(f'미국채10Y 상승 — 전력 인프라 비용 부담 -1점')
            elif tnx<=-0.05: adj+=1; notes.append(f'미국채10Y 하락 — 전력 인프라 투자 우호 +1점')
    return {'adjustment':adj,'max_bonus':5,'max_penalty':-10,'notes':notes}

def build_flags(s, t, fund, flow, tech, mkt_env):
    m=flow['metrics']; rsi=t.get('RSI',50); bb_pos=t.get('BB위치','밴드내')
    return {
        'overheated':                    rsi>=75 or bb_pos=='상단돌파',
        'pullback_candidate':            rsi<=45 and t.get('MA상승수',0)>=3,
        'trend_strong':                  t.get('MA상승수',0)>=3 and t.get('골든크로스',False),
        'flow_confirmed':                m['foreign_direction']==1 and m['institution_direction']==1,
        'foreign_institution_divergence':(m['foreign_direction'] is not None and m['institution_direction'] is not None and m['foreign_direction']!=m['institution_direction']),
        'retail_absorption_risk':        (m['retail_direction']==1 and m['foreign_direction']==-1 and m['institution_direction']==-1),
        'program_driven_risk':           m['program_driven_risk'],
        'valuation_risk':                fund['details']['valuation_burden']['score']<=2,
        'event_risk':                    False,
        'downtrend_rebound_only':        rsi<=35 and t.get('MA상승수',0)<=1,
        'market_stress':                 mkt_env['adjustment']<=-4,
    }

def build_summary(s, t, name, fund, flow, tech, flags, mkt_env):
    m=flow['metrics']; pos,neg,unc,ver=[],[],[],[]
    if flags.get('flow_confirmed'):                 pos.append('외국인·기관 동시 순매수 — 수급 방향 일치')
    if flags.get('trend_strong'):                   pos.append('MACD 골든크로스 + MA 상승배열 — 추세 확인')
    if fund['details']['valuation_burden']['score']>=4: pos.append('PBR·PER 업종 대비 저평가·적정')
    if fund['details']['risk_manageability']['score']>=4: pos.append('52주 고가 대비 충분한 조정 + MA 회복 — 눌림목 후보')
    if flags.get('pullback_candidate'):             pos.append('상승 추세 내 눌림목 구간(RSI 45 이하) — 가격 부담 낮은 진입 후보')
    frgn_pct=m.get('foreign_pct_mktcap')
    if frgn_pct and frgn_pct>=0.1 and m.get('foreign_direction')==1:
        pos.append(f'외국인 시총대비 +{frgn_pct:.3f}% 대규모 순매수 — 강한 수급 유입')
    if flags.get('overheated'):               neg.append(f'RSI {t.get("RSI","-")} / %B {t.get("%B","-")} — 과열. 신규 진입 부담')
    if flags.get('retail_absorption_risk'):   neg.append('개인 매수 + 외국인·기관 이탈 — 물량 흡수 위험')
    if flags.get('valuation_risk'):           neg.append('PBR·PER 업종 대비 고평가')
    if flags.get('foreign_institution_divergence'): neg.append('외국인·기관 방향 엇갈림 — 수급 불확실')
    if flags.get('program_driven_risk'):      neg.append('프로그램 매매 비중 과다 — 개별 펀더멘털 신호 아닐 수 있음')
    if flags.get('market_stress'):            neg.append(f'시장 환경 악화 (페널티 {mkt_env["adjustment"]}점)')
    if m['foreign_source']=='당일':  unc.append('외국인 수급 — 당일만 반영 (5일 누적 없음)')
    if m['institution_source']=='당일': unc.append('기관 수급 — 당일만 반영 (5일 누적 없음)')
    unc.append('실적 추정치·수주잔고 — 정성 데이터 미반영')
    unc.append('업종 상대강도 — 동종 종목 비교 없음')
    ver.append('외국인·기관 5일 누적 순매수 방향 직접 확인')
    ver.append('업종 동향 및 동종 종목 상대강도 확인')
    if flags.get('overheated'):                    ver.append('눌림목·조정 대기 후 재검토')
    if fund['details']['event_momentum']['score']<=4: ver.append('수주·실적·정책 이벤트 캘린더 확인')
    return {'core_positive_points':pos,'core_negative_points':neg,'key_uncertainties':unc,'items_to_verify_next':ver}

def score_stock(name, s, t, market):
    sector=SECTOR_MAP.get(name,'기타'); stock_type=STOCK_TYPES.get(name,['데이터 부족으로 분류 보류'])
    missing=[]
    if is_missing(s.get('외국인_5일순매수금')) and is_missing(s.get('외국인_순매수금')): missing.append('외국인 수급')
    if is_missing(s.get('기관_5일순매수금')) and is_missing(s.get('기관_순매수금')):   missing.append('기관 수급')
    if is_missing(s.get('거래대금')) or s.get('거래대금')==0:   missing.append('거래대금')
    if is_missing(s.get('PER')) or s.get('PER')==0:             missing.append('PER')
    if is_missing(s.get('PBR')) or s.get('PBR')==0:             missing.append('PBR')
    quality='충분' if len(missing)==0 else ('일부 부족' if len(missing)<=2 else '부족')
    caution=f'누락: {", ".join(missing)}' if missing else ''
    fund=score_fundamental(s,t,name); flow=score_flow(s)
    tech=score_technical(t);          mkt_env=score_market_env(market,name)
    raw=fund['total']+flow['total']+tech['total']
    adj=max(0,min(100,raw+mkt_env['adjustment']))
    if adj>=80:   grade='적극 관심'
    elif adj>=65: grade='관심'
    elif adj>=50: grade='관망'
    elif adj>=35: grade='주의'
    else:         grade='배제'
    flags=build_flags(s,t,fund,flow,tech,mkt_env)
    summary=build_summary(s,t,name,fund,flow,tech,flags,mkt_env)
    return {'stock_name':name,'sector':sector,'stock_type':stock_type,
            'data_quality':{'overall':quality,'missing_fields':missing,'caution':caution},
            'scores':{'fundamental_industry':fund,'flow':flow,'technical':tech,
                      'market_environment':mkt_env,
                      'total':{'raw_score':raw,'adj_score':adj,'adjustment':mkt_env['adjustment'],
                               'max':100,'grade':grade,
                               'note':'총점은 매수·매도 결론이 아니라 관찰 우선순위입니다.'}},
            'flags':flags,'summary_for_stage_2':summary}

def generate_stage2_report(result, stock_data, tech_data, market_data):
    name       = result['stock_name']
    sector     = result['sector']
    stock_type = ', '.join(result['stock_type'])
    total      = result['scores']['total']
    fund       = result['scores']['fundamental_industry']
    flow       = result['scores']['flow']
    tech_sc    = result['scores']['technical']
    mkt        = result['scores']['market_environment']
    flags      = result['flags']
    summary    = result['summary_for_stage_2']
    metrics    = flow['metrics']
    s          = stock_data.get(name, {})
    t          = tech_data.get(name, {})
    rsi        = t.get('RSI', 50)
    pctb       = safe_float(t.get('%B', 50))
    ma         = t.get('MA상승수', 0)
    vr         = safe_float(t.get('거래량비율(%)', 100))
    bb_pos     = t.get('BB위치', '밴드내')
    golden     = t.get('골든크로스', False)
    w52h       = safe_float(s.get('52주고가대비(%)', 0))
    lines      = []
    lines.append('[1] 종목 요약')
    lines.append(f'  종목명:   {name}')
    lines.append(f'  업종/유형: {sector} / {stock_type}')
    lines.append(f'  총점:     {total["adj_score"]}/100  ({total["grade"]})')
    lines.append(f'  현재가:   {s.get("현재가",0):,}원  ({s.get("등락률(%)",0):+.2f}%)')
    lines.append(f'  시가총액: {s.get("시가총액(억)",0):,}억원')
    lines.append(f'  데이터:   {result["data_quality"]["overall"]}')
    if result['data_quality']['caution']: lines.append(f'  ※ {result["data_quality"]["caution"]}')
    lines.append('')
    lines.append('[2] 총평')
    if fund['total']>=32:    lines.append('  ✦ 좋은 종목인가:  펀더멘털·산업 점수 양호. 중장기 보유 근거 있음.')
    elif fund['total']>=24:  lines.append('  ✦ 좋은 종목인가:  펀더멘털·산업 점수 보통. 업황 확인 후 판단 권장.')
    else:                    lines.append('  ✦ 좋은 종목인가:  펀더멘털·산업 점수 낮음. 추가 확인 필요.')
    if flags.get('overheated'):
        if rsi>=85: lines.append(f'  ✦ 좋은 가격인가:  RSI {rsi} / %B {pctb}% — 심각한 과열. 신규 진입 가격 부담 높음.')
        else:       lines.append(f'  ✦ 좋은 가격인가:  RSI {rsi} / %B {pctb}% — 과열 구간. 신규 진입 부담 있음.')
    elif flags.get('pullback_candidate'): lines.append(f'  ✦ 좋은 가격인가:  RSI {rsi} — 상승 추세 내 눌림목 구간. 상대적으로 가격 부담 낮음.')
    elif rsi<=35:                         lines.append(f'  ✦ 좋은 가격인가:  RSI {rsi} — 과매도 구간. 단, 하락 추세 중이면 저점 단정 금지.')
    else:                                 lines.append(f'  ✦ 좋은 가격인가:  RSI {rsi} — 중립 구간. 수급과 추세 방향 확인 필요.')
    if flags.get('overheated') and not flags.get('flow_confirmed'):  lines.append('  ✦ 신규진입 적합도: 낮음 — 과열 + 수급 미확인. 관망 또는 소량 분할만 고려.')
    elif flags.get('overheated') and flags.get('flow_confirmed'):    lines.append('  ✦ 신규진입 적합도: 주의 — 수급은 확인됐으나 과열. 추격보다 눌림 대기 권장.')
    elif flags.get('pullback_candidate') and flags.get('flow_confirmed'): lines.append('  ✦ 신규진입 적합도: 양호 — 눌림목 + 수급 확인. 1차 진입 검토 가능.')
    elif flags.get('flow_confirmed'):                                lines.append('  ✦ 신규진입 적합도: 보통 — 수급 확인. 기술적 진입 타이밍 추가 확인 필요.')
    elif flags.get('foreign_institution_divergence'):               lines.append('  ✦ 신규진입 적합도: 낮음 — 외국인·기관 방향 엇갈림. 수급 방향 확인 후 진입.')
    else:                                                            lines.append('  ✦ 신규진입 적합도: 보통 — 뚜렷한 진입 신호 없음. 관망 유지.')
    if ma>=3 and flags.get('flow_confirmed'):  lines.append('  ✦ 보유지속 적합도: 양호 — MA 상승배열 + 수급 유지. 추세 훼손 전까지 보유 근거 있음.')
    elif ma>=3 and flags.get('overheated'):    lines.append('  ✦ 보유지속 적합도: 조건부 — 추세 강하나 과열. 일부 차익실현 병행 고려.')
    elif ma<=1:                                lines.append('  ✦ 보유지속 적합도: 낮음 — MA 하락배열. 추세 회복 신호 전까지 비중 유지 주의.')
    else:                                      lines.append('  ✦ 보유지속 적합도: 보통 — 추세 방향 확인 중. 수급 유지 여부 모니터링 필요.')
    chase_risk_count=sum([rsi>=75, pctb>=100, vr>=200, flags.get('overheated',False),
                          flags.get('retail_absorption_risk',False),
                          flags.get('foreign_institution_divergence',False), w52h>=-5])
    if chase_risk_count>=4:   lines.append(f'  ✦ 추격매수 위험도: 높음 ({chase_risk_count}/7 조건 충족) — 신규 진입 자제 권고.')
    elif chase_risk_count>=2: lines.append(f'  ✦ 추격매수 위험도: 중간 ({chase_risk_count}/7 조건 충족) — 분할 접근 또는 눌림 대기.')
    else:                     lines.append(f'  ✦ 추격매수 위험도: 낮음 ({chase_risk_count}/7 조건 충족).')
    lines.append('')
    lines.append('[3] 점수 해석')
    lines.append(f'  펀더멘털·산업 {fund["total"]}/40')
    for k,lbl in [('industry_growth','산업성장성'),('earnings_visibility','실적가시성'),('event_momentum','이벤트모멘텀'),('valuation_burden','밸류에이션'),('risk_manageability','리스크관리')]:
        d=fund['details'][k]; lines.append(f'    {lbl:8s} {d["score"]}/{d["max"]}: {d["reason"]}')
    lines.append(f'  수급 {flow["total"]}/30')
    for k,lbl in [('foreign_cumulative','외국인'),('institution_cumulative','기관'),('foreign_institution_alignment','방향일치'),('program_trading','프로그램')]:
        d=flow['details'][k]; lines.append(f'    {lbl:6s} {d["score"]}/{d["max"]}: {d["reason"]}')
    lines.append(f'  기술지표 {tech_sc["total"]}/30')
    for k,lbl in [('ma_alignment','MA배열'),('rsi','RSI'),('macd','MACD'),('percent_b','%B'),('bandwidth','밴드폭'),('volume','거래량')]:
        d=tech_sc['details'][k]; lines.append(f'    {lbl:6s} {d["score"]}/{d["max"]}: {d["reason"]}')
    lines.append(f'  시장환경 조정: {total["adjustment"]:+d}점')
    for n in mkt['notes']: lines.append(f'    {n}')
    lines.append('  ※ 총점은 매수·매도 결론이 아니라 관찰 우선순위입니다.')
    lines.append('')
    lines.append('[4] 긍정 요인')
    if summary['core_positive_points']:
        for p in summary['core_positive_points']: lines.append(f'  ✅ {p}')
    else: lines.append('  뚜렷한 긍정 요인 제한적.')
    lines.append('')
    lines.append('[5] 위험 요인')
    if summary['core_negative_points']:
        for n in summary['core_negative_points']: lines.append(f'  ⚠️  {n}')
    else: lines.append('  뚜렷한 위험 플래그 제한적.')
    lines.append('')
    lines.append('[6] 반대 시나리오')
    bull=[]
    if flags.get('flow_confirmed'):     bull.append('외국인·기관 동반 매수 지속 → 수급 주도 상승 연장 가능')
    if golden:                          bull.append('MACD 골든크로스 유지 + 거래량 증가 → 추세 강화')
    if fund['details']['risk_manageability']['score']>=4: bull.append('52주 충분한 조정 후 MA 회복 → 눌림목 매수 유입 가능')
    if fund['details']['event_momentum']['score']>=7:     bull.append('수주·정책 이벤트 추가 확인 → 모멘텀 연장')
    if not bull: bull.append('시장 전반 강세 + 업종 상대강도 회복 시 동반 상승 가능')
    lines.append('  상승 시나리오:')
    for b in bull: lines.append(f'    • {b}')
    bear=[]
    if flags.get('overheated'):                    bear.append(f'RSI {rsi} 과열 이후 거래량 동반 음봉 → 단기 급락 가능')
    if flags.get('foreign_institution_divergence'):bear.append('외국인·기관 수급 엇갈림 지속 → 방향성 약화')
    if flags.get('retail_absorption_risk'):        bear.append('개인 물량 흡수 중 → 외국인·기관 이탈 시 급락 위험')
    if flags.get('program_driven_risk'):           bear.append('프로그램 매수 소멸 시 → 지지 약화 가능')
    if flags.get('valuation_risk'):                bear.append('고평가 상태에서 실적 기대 미달 → 밸류에이션 조정 위험')
    if not bear: bear.append('시장 전반 약세 + 환율·금리 악화 시 동반 하락 가능')
    lines.append('  하락 시나리오:')
    for b in bear: lines.append(f'    • {b}')
    lines.append('  분석이 틀렸다고 볼 조건:')
    lines.append('    • 20일 이동평균선 종가 이탈')
    lines.append('    • 외국인·기관 3거래일 이상 동반 순매도')
    lines.append('    • 거래량 동반 장대음봉 출현')
    if fund['details']['event_momentum']['score']>=7: lines.append('    • 주요 수주·정책 이벤트 지연 또는 무산')
    lines.append('    • 업종 ETF 또는 대표주 상대강도 훼손')
    lines.append('')
    lines.append('[7] 매매 전략')
    if flags.get('overheated') and flags.get('flow_confirmed'):
        lines.append('  신규 진입:  지금은 추격에 가깝습니다.')
        lines.append('    → RSI·%B 과열 해소(RSI 60 이하, %B 80 이하) 후 재검토')
        lines.append('    → 분할 접근 시 1차는 소량(목표 비중의 1/3 이내)으로 제한')
    elif flags.get('overheated') and not flags.get('flow_confirmed'):
        lines.append('  신규 진입:  과열 + 수급 미확인. 진입 자제 권고.')
        lines.append('    → 수급 방향 확인 + 기술적 과열 해소 동시 확인 후 재검토')
    elif flags.get('pullback_candidate') and flags.get('flow_confirmed'):
        lines.append('  신규 진입:  눌림목 후보. 1차 진입 검토 가능합니다.')
        lines.append('    → 1차 진입 조건: 20일선 지지 확인 + 거래량 감소 조정')
        lines.append('    → 추가 진입 조건: 외국인·기관 수급 유지 확인')
        lines.append('    → 실패 조건: 20일선 종가 이탈 시 손절')
    elif flags.get('downtrend_rebound_only'):
        lines.append('  신규 진입:  과매도 반등 가능하나 하락 추세 반등주 가능성 있습니다.')
        lines.append('    → MA 배열 회복, 거래량 동반 양봉 확인 전까지 진입 보류')
    else:
        lines.append('  신규 진입:  현 구간은 관망 또는 소량 분할 접근이 적합합니다.')
        lines.append('    → 수급 방향 확인 전까지 비중 확대 신중')
    lines.append('  분할 매수 조건:')
    if flags.get('overheated'):
        lines.append('    • RSI 60 이하 + %B 80 이하 회귀 시 1차')
        lines.append('    • 20일선 지지 확인 + 거래량 감소 조정 시 2차')
    else:
        lines.append('    • 20일선 부근 + 거래량 감소 조정 시 1차')
        lines.append('    • 외국인·기관 수급 재확인 시 2차')
    lines.append('    • 비중은 목표의 1/3씩 분할 접근 권장')
    lines.append('  비중 확대 조건:')
    lines.append('    • 외국인·기관 동반 순매수 3거래일 이상 지속')
    lines.append('    • 업종 상대강도 유지 또는 강화')
    lines.append('    • 시장 환경 우호적 (VIX 안정, 코스피 상승)')
    if flags.get('overheated'): lines.append('    ※ 현재 과열 구간 — 비중 확대 보류')
    lines.append('  차익실현 조건:')
    if flags.get('overheated'):
        lines.append('    • 현재 과열 구간 — 보유자는 일부 차익실현 고려')
        lines.append('    • RSI 85 이상 + 거래량 급감 시 30~50% 부분 익절')
    lines.append('    • 외국인·기관 동반 순매도 전환 시 비중 축소')
    lines.append('    • 전량 매도보다 트레일링 방식 권장 (추세 훼손 신호 대기)')
    lines.append('  손절·비중 축소 조건:')
    lines.append('    • 20일 이동평균선 종가 이탈')
    lines.append('    • 외국인·기관 3거래일 이상 동반 순매도')
    lines.append('    • 거래량 동반 장대음봉 출현')
    if '정책·수주 모멘텀주' in stock_type: lines.append('    • 주요 수주·정책 이벤트 지연 또는 무산')
    lines.append('  관망 조건:')
    lines.append('    • 외국인·기관 수급 방향 불명확')
    lines.append('    • VIX 20 이상 시장 불안 구간')
    if flags.get('foreign_institution_divergence'): lines.append('    • 현재 수급 엇갈림 — 방향 확인 전까지 관망 권장')
    lines.append('')
    lines.append('[8] 업데이트 트리거')
    lines.append('  내일 확인:')
    lines.append('    • 외국인·기관 수급 방향 유지 여부')
    cur_price=s.get('현재가',0)
    lines.append(f'    • 20일 이동평균선({int(cur_price*0.95):,}원 부근) 지지 여부')
    lines.append('    • 거래량 수준 (평균 대비 증감)')
    if flags.get('overheated'): lines.append('    • RSI·%B 과열 지속 여부')
    lines.append('  이번 주 확인:')
    lines.append('    • 5일 누적 외국인·기관 순매수 방향')
    lines.append('    • 업종 동향 및 동종 종목 상대강도')
    lines.append('    • 코스피200 방향 유지 여부')
    lines.append('  실적·이벤트 확인:')
    for v in summary['items_to_verify_next']: lines.append(f'    • {v}')
    lines.append('  시장 변수 확인:')
    lines.append('    • VIX 수준 (20 이상 시 리스크 관리 강화)')
    lines.append('    • 원/달러 환율 방향 (수출주 영향)')
    if name in SOX_LINKED:      lines.append('    • SOX 지수 방향 (반도체 업종 선행)')
    if name in AI_POWER_LINKED: lines.append('    • 구리 가격, 미국채 10Y (AI 전력 인프라 수요)')
    lines.append('')
    lines.append('[9] 현재 분석의 한계')
    for u in summary['key_uncertainties']: lines.append(f'  • {u}')
    lines.append('')
    lines.append('[10] 최종 판단')
    lines.append(f'  등급: {total["grade"]}')
    if total['adj_score']>=80:   reason='펀더멘털·수급·기술지표 전반 양호. 단, 가격 위치와 과열 여부 추가 확인 필요.'
    elif total['adj_score']>=65:
        if flags.get('overheated'):        reason='관심권 종목이나 현재 과열 구간. 눌림목 또는 수급 재확인 후 접근 권장.'
        elif flags.get('flow_confirmed'):  reason='수급 방향 확인. 기술적 진입 타이밍 추가 확인 후 접근 가능.'
        else:                              reason='관심권이나 수급 지속성 불확실. 방향 확인 후 판단 권장.'
    elif total['adj_score']>=50: reason='관망 구간. 뚜렷한 방향성 신호 전까지 무리한 진입 자제.'
    elif total['adj_score']>=35: reason='주의 구간. 단기 반등 외에는 진입 근거 약함.'
    else:                        reason='현재 데이터 기준 우선순위 낮음. 재검토 시점까지 배제.'
    lines.append(f'  이유:  {reason}')
    lines.append('  주의:  본 분석은 정량 데이터 기반 보조 의견입니다.')
    lines.append('         투자 결정의 최종 책임은 본인에게 있습니다.')
    lines.append('         5일 누적 수급·실적 추정치·수주잔고 등 미반영 항목을 반드시 교차 확인하세요.')
    return '\n'.join(lines)