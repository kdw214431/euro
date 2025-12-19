import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from github import Github
from io import StringIO
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="GitHub 연동 가계부", page_icon="🐙")

# --- GitHub 연결 함수 ---
def get_github_repo():
    token = st.secrets["github"]["token"]
    g = Github(token)
    repo_path = f"{st.secrets['github']['username']}/{st.secrets['github']['repo_name']}"
    return g.get_repo(repo_path)

def load_data_from_github():
    try:
        repo = get_github_repo()
        contents = repo.get_contents("expenses.csv", ref=st.secrets["github"]["branch"])
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        return pd.DataFrame(columns=["날짜", "항목", "통화", "외화금액", "환율", "한국돈(원)"])

def save_data_to_github(new_df):
    repo = get_github_repo()
    csv_content = new_df.to_csv(index=False)
    branch = st.secrets["github"]["branch"]
    try:
        contents = repo.get_contents("expenses.csv", ref=branch)
        repo.update_file(contents.path, "가계부 업데이트", csv_content, contents.sha, branch=branch)
    except:
        repo.create_file("expenses.csv", "초기 파일 생성", csv_content, branch=branch)

# --- 환율 정보 함수 (캐싱 적용으로 속도 향상) ---
@st.cache_data(ttl=600) # 10분마다 갱신 (너무 자주 요청하면 차단될 수 있어서)
def get_exchange_rate(target_code):
    try:
        url = "https://finance.naver.com/marketindex/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        selector = f"#exchangeList a.head.{target_code} > div > span.value"
        rate_text = soup.select_one(selector).text
        return float(rate_text.replace(",", ""))
    except:
        return 0.0

# --- 메인 화면 ---
st.title("가계부")
st.caption("실시간 환율 확인 & 지출 내역 자동 저장")

tab1, tab2 = st.tabs(["💱 환율 계산기", "📝 지출 기록장"])

# ==========================================
# 탭 1: 계산기
# ==========================================
with tab1:
    st.header("실시간 환율 계산")
    
    # 1. 통화 선택
    currency = st.radio("통화 선택", ["🇺🇸 USD", "🇪🇺 EUR", "🇯🇵 JPY"], horizontal=True, key="t1_radio")
    
    # 2. 선택하자마자 환율 가져오기
    if "USD" in currency: code, symbol, j = "usd", "$", False
    elif "EUR" in currency: code, symbol, j = "eur", "€", False
    else: code, symbol, j = "jpy", "¥", True
    
    current_rate = get_exchange_rate(code)
    
    # 3. 환율 정보 보여주기 (여기가 추가된 부분!)
    if j: # 엔화는 100엔 기준
        st.info(f"🇯🇵 현재 100엔 = **{current_rate:,.2f} 원**")
    elif "EUR" in currency:
        st.info(f"🇪🇺 현재 1유로 = **{current_rate:,.2f} 원**")
    else:
        st.info(f"🇺🇸 현재 1달러 = **{current_rate:,.2f} 원**")

    # 4. 금액 입력 및 계산
    val = st.number_input(f"금액 ({symbol})", min_value=0.0, value=None, key="t1_input")
    
    if st.button("계산하기", key="t1_btn"):
        if val:
            krw = val * (current_rate/100) if j else val * current_rate
            st.success(f"약 {int(krw):,} 원")

# ==========================================
# 탭 2: 가계부
# ==========================================
with tab2:
    st.header("지출 내역 추가")
    
    col1, col2 = st.columns([2, 1])
    with col1: item = st.text_input("내역 (예: 편의점)", key="t2_item")
    with col2: date = st.date_input("날짜", key="t2_date")
    
    # 여기서도 통화를 선택하면 환율을 미리 보여줍니다
    c_type = st.selectbox("통화", ["USD", "EUR", "JPY"], key="t2_select")
    
    if "USD" in c_type: c_code, c_sym, is_j = "usd", "$", False
    elif "EUR" in c_type: c_code, c_sym, is_j = "eur", "€", False
    else: c_code, c_sym, is_j = "jpy", "¥", True
    
    # 환율 미리 가져오기
    rate_now = get_exchange_rate(c_code)
    st.caption(f"현재 적용 환율: {rate_now:,.2f}원" + (" (100엔 당)" if is_j else ""))

    amt = st.number_input(f"금액 ({c_sym})", min_value=0.0, value=None, key="t2_amt")
    
    if st.button("GitHub에 저장하기", type="primary", key="t2_btn"):
        if not item or not amt:
            st.warning("내용과 금액을 입력해주세요.")
        else:
            with st.spinner("저장 중..."):
                final_krw = int(amt * (rate_now/100)) if is_j else int(amt * rate_now)
                
                df = load_data_from_github()
                new_row = pd.DataFrame([{
                    "날짜": str(date), "항목": item, "통화": c_type,
                    "외화금액": amt, "환율": rate_now, "한국돈(원)": final_krw
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data_to_github(df)
                
                st.success(f"저장 완료! ({final_krw:,}원)")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # 저장된 목록 보여주기
    if st.checkbox("📋 저장된 목록 보기"):
        df_view = load_data_from_github()
        if not df_view.empty:
            st.dataframe(df_view, use_container_width=True)
            if "한국돈(원)" in df_view.columns:
                 st.metric("총 지출", f"{df_view['한국돈(원)'].sum():,} 원")
        else:
            st.info("데이터가 없습니다.")