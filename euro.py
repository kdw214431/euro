import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from github import Github
from io import StringIO
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="우리들의 여행 가계부", page_icon="✈️")

# ==========================================
# ⚠️ 멤버 이름은 여기서 수정하세요!
# ==========================================
MEMBERS = ["김단우", "장효진", "김예진", "진우씨", "멤버1", "공동경비"]

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
        return pd.DataFrame(columns=["날짜", "결제자", "항목", "통화", "외화금액", "환율", "한국돈(원)"])

def save_data_to_github(new_df):
    repo = get_github_repo()
    csv_content = new_df.to_csv(index=False)
    branch = st.secrets["github"]["branch"]
    try:
        contents = repo.get_contents("expenses.csv", ref=branch)
        repo.update_file(contents.path, "가계부 업데이트", csv_content, contents.sha, branch=branch)
    except:
        repo.create_file("expenses.csv", "초기 파일 생성", csv_content, branch=branch)

# --- 환율 정보 함수 ---
@st.cache_data(ttl=600)
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
st.title("✈️ 우리들의 여행 가계부")
st.caption("실수로 잘못 입력했다면 '삭제' 버튼을 눌러주세요.")

tab1, tab2 = st.tabs(["💱 환율 계산기", "📝 공동 지출 기록"])

# 탭 1: 계산기
with tab1:
    st.header("실시간 환율 계산")
    currency = st.radio("통화 선택", ["🇺🇸 USD", "🇪🇺 EUR", "🇯🇵 JPY"], horizontal=True, key="t1_radio")
    
    if "USD" in currency: code, symbol, j = "usd", "$", False
    elif "EUR" in currency: code, symbol, j = "eur", "€", False
    else: code, symbol, j = "jpy", "¥", True
    
    current_rate = get_exchange_rate(code)
    
    if j: st.info(f"🇯🇵 현재 100엔 = **{current_rate:,.2f} 원**")
    elif "EUR" in currency: st.info(f"🇪🇺 현재 1유로 = **{current_rate:,.2f} 원**")
    else: st.info(f"🇺🇸 현재 1달러 = **{current_rate:,.2f} 원**")

    val = st.number_input(f"금액 ({symbol})", min_value=0.0, value=None, key="t1_input")
    if st.button("계산하기", key="t1_btn"):
        if val:
            krw = val * (current_rate/100) if j else val * current_rate
            st.success(f"약 {int(krw):,} 원")

# 탭 2: 공동 가계부
with tab2:
    st.header("💸 지출 내역 관리")
    
    # 입력 폼
    who = st.selectbox("누가 결제했나요?", MEMBERS)
    col1, col2 = st.columns([2, 1])
    with col1: item = st.text_input("내역 (예: 점심)", key="t2_item")
    with col2: date = st.date_input("날짜", key="t2_date")
    
    c_type = st.selectbox("통화", ["USD", "EUR", "JPY"], key="t2_select")
    if "USD" in c_type: c, sym, j = "usd", "$", False
    elif "EUR" in c_type: c, sym, j = "eur", "€", False
    else: c, sym, j = "jpy", "¥", True
    
    r_now = get_exchange_rate(c)
    amt = st.number_input(f"금액 ({sym})", min_value=0.0, value=None, key="t2_amt")
    
    # 버튼들을 가로로 배치
    b_col1, b_col2 = st.columns(2)
    
    # 1. 저장 버튼
    with b_col1:
        if st.button("GitHub에 저장하기", type="primary", use_container_width=True):
            if not item or not amt:
                st.warning("내용과 금액을 입력해주세요.")
            else:
                with st.spinner("저장 중..."):
                    krw = int(amt * (r_now/100)) if j else int(amt * r_now)
                    df = load_data_from_github()
                    new_row = pd.DataFrame([{
                        "날짜": str(date), "결제자": who, "항목": item, "통화": c_type,
                        "외화금액": amt, "환율": r_now, "한국돈(원)": krw
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data_to_github(df)
                    st.success("저장 완료!")
                    time.sleep(1)
                    st.rerun()

    # 2. 삭제 버튼 (새로 추가된 기능!)
    with b_col2:
        if st.button("↩️ 방금 저장한거 취소", use_container_width=True):
            with st.spinner("마지막 내역을 지우는 중..."):
                df = load_data_from_github()
                if not df.empty:
                    # 마지막 한 줄 제외하고 다시 저장 (슬라이싱)
                    df = df.iloc[:-1]
                    save_data_to_github(df)
                    st.success("마지막 내역이 삭제되었습니다.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("삭제할 데이터가 없습니다.")
    
    st.divider()
    
    # 내역 보여주기
    st.subheader("📋 지출 내역")
    df_view = load_data_from_github()
    if not df_view.empty:
        opt = st.radio("필터:", ["전체 보기"] + MEMBERS, horizontal=True)
        if opt == "전체 보기":
            st.dataframe(df_view, use_container_width=True)
            st.metric("총 지출", f"{df_view['한국돈(원)'].sum():,} 원")
        else:
            f_df = df_view[df_view["결제자"] == opt]
            st.dataframe(f_df, use_container_width=True)
            if not f_df.empty:
                st.metric(f"{opt}님 사용액", f"{f_df['한국돈(원)'].sum():,} 원")
    else:
        st.info("데이터가 없습니다.")