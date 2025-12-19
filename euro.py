import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

# --- 페이지 설정 ---
st.set_page_config(page_title="여행 가계부 & 계산기", page_icon="✈️")

# --- 환율 정보 가져오는 함수 ---
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

# --- 데이터 파일 관리 (CSV) ---
CSV_FILE = "my_expenses.csv"

def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        # 파일이 없으면 빈 표를 만듭니다.
        return pd.DataFrame(columns=["날짜", "항목", "통화", "외화금액", "환율", "한국돈(원)"])

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# --- 메인 화면 시작 ---
st.title("✈️ 똑똑한 여행 가계부")

# 탭 만들기 (화면 분리)
tab1, tab2 = st.tabs(["💱 환율 계산기", "📝 지출 기록장"])

# ==========================================
# 탭 1: 기존 환율 계산기 기능
# ==========================================
with tab1:
    st.header("실시간 환율 계산")
    
    currency = st.radio(
        "통화를 선택해주세요",
        ["🇺🇸 미국 달러 (USD)", "🇪🇺 유럽 연합 (EUR)", "🇯🇵 일본 엔 (JPY)"],
        horizontal=True,
        key="calc_radio"
    )

    # 설정 변수
    if "미국" in currency:
        code, symbol, is_jpy = "usd", "$", False
    elif "유럽" in currency:
        code, symbol, is_jpy = "eur", "€", False
    else:
        code, symbol, is_jpy = "jpy", "¥", True

    money_input = st.number_input(f"금액 입력 ({symbol})", min_value=0.0, value=None, step=1.0, key="calc_input")

    if st.button("계산하기", key="calc_btn"):
        if money_input:
            rate = get_exchange_rate(code)
            if is_jpy:
                krw = money_input * (rate / 100)
                rate_info = f"100엔 = {rate}원"
            else:
                krw = money_input * rate
                rate_info = f"1{symbol} = {rate}원"
            
            st.success(f"적용 환율: {rate_info}")
            st.markdown(f"### 🇰🇷 약 {int(krw):,} 원")

# ==========================================
# 탭 2: 가계부 (새로 추가된 기능!)
# ==========================================
with tab2:
    st.header("무엇을 썼나요?")
    
    # 1. 입력 폼 만들기
    col1, col2 = st.columns([2, 1])
    with col1:
        item_name = st.text_input("지출 내역 (예: 점심, 기념품)")
    with col2:
        date = st.date_input("날짜")

    # 통화 및 금액 입력
    col3, col4 = st.columns(2)
    with col3:
        exp_currency = st.selectbox("통화 선택", ["USD ($)", "EUR (€)", "JPY (¥)"])
    with col4:
        exp_amount = st.number_input("금액", min_value=0.0, step=1.0)

    # 추가 버튼
    if st.button("기록 추가하기", type="primary"):
        if not item_name or exp_amount == 0:
            st.warning("내역과 금액을 입력해주세요!")
        else:
            with st.spinner("환율 계산 후 저장 중..."):
                # 통화 코드 매핑
                if "USD" in exp_currency:
                    c_code, is_j = "usd", False
                elif "EUR" in exp_currency:
                    c_code, is_j = "eur", False
                else:
                    c_code, is_j = "jpy", True
                
                # 환율 가져오기 및 계산
                current_rate = get_exchange_rate(c_code)
                if is_j:
                    final_krw = int(exp_amount * (current_rate / 100))
                else:
                    final_krw = int(exp_amount * current_rate)

                # 데이터 저장하기
                df = load_data()
                new_data = {
                    "날짜": date,
                    "항목": item_name,
                    "통화": exp_currency,
                    "외화금액": exp_amount,
                    "환율": current_rate,
                    "한국돈(원)": final_krw
                }
                # pandas concat을 이용해 행 추가 (최신 pandas 버전 대응)
                new_df = pd.DataFrame([new_data])
                df = pd.concat([df, new_df], ignore_index=True)
                save_data(df)
                
                st.success(f"저장 완료! ({final_krw:,}원)")
                time.sleep(1)
                st.rerun() # 화면 새로고침해서 표 업데이트

    st.markdown("---")
    
    # 2. 저장된 내역 보여주기
    st.subheader("📋 나의 지출 리스트")
    df = load_data()
    
    if not df.empty:
        # 보기 좋게 표 출력
        st.dataframe(df, use_container_width=True)
        
        # 총 합계 계산
        total_spent = df["한국돈(원)"].sum()
        st.metric(label="총 지출 금액 (KRW 환산)", value=f"{total_spent:,} 원")
        
        # 리셋 버튼 (데이터 삭제)
        if st.button("내역 초기화"):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
                st.rerun()
    else:
        st.info("아직 기록된 지출이 없습니다.")