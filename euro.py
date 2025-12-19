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
    """Secrets에 저장된 정보로 GitHub 저장소를 가져옵니다."""
    token = st.secrets["github"]["token"]
    g = Github(token)
    repo_path = f"{st.secrets['github']['username']}/{st.secrets['github']['repo_name']}"
    return g.get_repo(repo_path)

def load_data_from_github():
    """GitHub에 있는 expenses.csv 파일을 읽어옵니다."""
    try:
        repo = get_github_repo()
        # 파일 내용을 가져옴
        contents = repo.get_contents("expenses.csv", ref=st.secrets["github"]["branch"])
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        # 파일이 없으면 빈 데이터프레임 반환
        return pd.DataFrame(columns=["날짜", "항목", "통화", "외화금액", "환율", "한국돈(원)"])

def save_data_to_github(new_df):
    """데이터프레임을 GitHub expenses.csv 파일에 덮어씁니다."""
    repo = get_github_repo()
    csv_content = new_df.to_csv(index=False)
    branch = st.secrets["github"]["branch"]
    
    try:
        # 파일이 이미 있으면 업데이트(Update)
        contents = repo.get_contents("expenses.csv", ref=branch)
        repo.update_file(contents.path, "가계부 업데이트 (앱)", csv_content, contents.sha, branch=branch)
    except:
        # 파일이 없으면 새로 생성(Create)
        repo.create_file("expenses.csv", "가계부 파일 생성", csv_content, branch=branch)

# --- 환율 정보 함수 ---
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
st.title("🐙 GitHub 연동 가계부")
st.caption("카드 등록 없이! 데이터가 GitHub 저장소에 안전하게 저장됩니다.")

tab1, tab2 = st.tabs(["💱 환율 계산기", "📝 지출 기록장"])

# 탭 1: 계산기 (기존 동일)
with tab1:
    st.header("실시간 환율 계산")
    currency = st.radio("통화 선택", ["🇺🇸 USD", "🇪🇺 EUR", "🇯🇵 JPY"], horizontal=True)
    if "USD" in currency: code, symbol, j = "usd", "$", False
    elif "EUR" in currency: code, symbol, j = "eur", "€", False
    else: code, symbol, j = "jpy", "¥", True
    
    val = st.number_input(f"금액 ({symbol})", min_value=0.0, value=None)
    if st.button("계산"):
        if val:
            r = get_exchange_rate(code)
            k = val * (r/100) if j else val * r
            st.success(f"약 {int(k):,} 원")

# 탭 2: 가계부 (GitHub 연동)
with tab2:
    st.header("지출 내역 추가")
    
    col1, col2 = st.columns([2, 1])
    with col1: item = st.text_input("내역 (예: 편의점)")
    with col2: date = st.date_input("날짜")
    
    col3, col4 = st.columns(2)
    with col3: c_type = st.selectbox("통화", ["USD", "EUR", "JPY"])
    with col4: amt = st.number_input("금액", min_value=0.0)
    
    if st.button("GitHub에 저장하기", type="primary"):
        if not item or amt == 0:
            st.warning("내용을 입력해주세요.")
        else:
            with st.spinner("GitHub에 커밋하는 중... (3~5초 소요)"):
                # 1. 환율 계산
                if "USD" in c_type: c, j = "usd", False
                elif "EUR" in c_type: c, j = "eur", False
                else: c, j = "jpy", True
                
                rate = get_exchange_rate(c)
                krw = int(amt * (rate/100)) if j else int(amt * rate)
                
                # 2. 기존 데이터 가져오기
                df = load_data_from_github()
                
                # 3. 새 데이터 추가
                new_row = pd.DataFrame([{
                    "날짜": str(date), "항목": item, "통화": c_type,
                    "외화금액": amt, "환율": rate, "한국돈(원)": krw
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                
                # 4. GitHub에 저장 (커밋)
                save_data_to_github(df)
                
                st.success(f"저장 성공! GitHub 저장소를 확인해보세요.")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    st.subheader("📋 저장된 목록 (GitHub)")
    if st.button("새로고침"):
        st.rerun()
        
    df_view = load_data_from_github()
    if not df_view.empty:
        st.dataframe(df_view, use_container_width=True)
        if "한국돈(원)" in df_view.columns:
            st.metric("총 지출", f"{df_view['한국돈(원)'].sum():,} 원")
    else:
        st.info("아직 저장된 데이터가 없습니다.")