import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from github import Github
from io import StringIO
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="우리들의 여행 가계부", page_icon="✈️")

# --- 설정: 우리 그룹 멤버 이름 (여기 이름을 자유롭게 바꾸세요!) ---
MEMBERS = ["나(김단우)", "친구A", "친구B", "공동경비"]

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
        # '결제자' 컬럼이 추가되었습니다!
        return pd.DataFrame(columns=["날짜", "결제자", "항목", "통화", "외화금액", "환율", "한국돈(원)"])

def save_data_to_github(new_df):
    repo = get_github_repo()
    csv_content = new_df.to_csv(index=False)
    branch = st.secrets["github"]["branch"]
    try:
        contents = repo.get_contents("expenses.csv", ref=branch)
        repo.update_file(contents.path, "공동 가계부 업데이트", csv_content, contents.sha, branch=branch)
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
st.caption("친구들과 링크를 공유해서 함께 기록하세요!")

tab1, tab2 = st.tabs(["💱 환율 계산기", "📝 공동 지출 기록"])

# 탭 1: 계산기 (이전과 동일)
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

# 탭 2: 공동 가계부 (업그레이드!)
with tab2:
    st.header("💸 지출 내역 추가")
    
    # 1. 누가 썼는지 선택
    who = st.selectbox("누가 결제했나요?", MEMBERS)
    
    col1, col2 = st.columns([2, 1])
    with col1: item = st.text_input("내역 (예: 저녁 식사)", key="t2_item")
    with col2: date = st.date_input("날짜", key="t2_date")
    
    c_type = st.selectbox("통화", ["USD", "EUR", "JPY"], key="t2_select")
    
    if "USD" in c_type: c_code, c_sym, is_j = "usd", "$", False
    elif "EUR" in c_type: c_code, c_sym, is_j = "eur", "€", False
    else: c_code, c_sym, is_j = "jpy", "¥", True
    
    rate_now = get_exchange_rate(c_code)
    amt = st.number_input(f"금액 ({c_sym})", min_value=0.0, value=None, key="t2_amt")
    
    if st.button("공동 장부에 저장하기", type="primary"):
        if not item or not amt:
            st.warning("내용과 금액을 입력해주세요.")
        else:
            with st.spinner("친구들과 공유하는 장부에 저장 중..."):
                final_krw = int(amt * (rate_now/100)) if is_j else int(amt * rate_now)
                
                df = load_data_from_github()
                # '결제자' 정보 포함해서 저장
                new_row = pd.DataFrame([{
                    "날짜": str(date), "결제자": who, "항목": item, "통화": c_type,
                    "외화금액": amt, "환율": rate_now, "한국돈(원)": final_krw
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data_to_github(df)
                
                st.success(f"[{who}]님의 지출이 저장되었습니다!")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # 2. 내역 보여주기 (필터링 기능 추가)
    st.subheader("📋 전체 지출 현황")
    
    # 데이터 불러오기
    df_view = load_data_from_github()
    
    if not df_view.empty:
        # 필터링 옵션
        filter_option = st.radio("보고 싶은 내역:", ["전체 보기"] + MEMBERS, horizontal=True)
        
        if filter_option == "전체 보기":
            st.dataframe(df_view, use_container_width=True)
            total = df_view['한국돈(원)'].sum()
            st.metric("우리 여행 총 지출", f"{total:,} 원")
        else:
            # 선택한 사람의 내역만 필터링
            filtered_df = df_view[df_view["결제자"] == filter_option]
            st.dataframe(filtered_df, use_container_width=True)
            if not filtered_df.empty:
                personal_total = filtered_df['한국돈(원)'].sum()
                st.metric(f"{filter_option}님이 쓴 총액", f"{personal_total:,} 원")
            else:
                st.info("아직 쓴 내역이 없네요.")
    else:
        st.info("아직 기록된 데이터가 없습니다.")