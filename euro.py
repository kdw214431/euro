import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# 페이지 기본 설정 (제목, 아이콘 등)
st.set_page_config(page_title="유로 계산기", page_icon="💶")

def get_euro_rate():
    """네이버 금융에서 실시간 유로 환율을 가져오는 함수"""
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    rate_text = soup.select_one("#exchangeList a.head.eur > div > span.value").text
    return float(rate_text.replace(",", ""))

# --- 웹 화면 구성 ---
st.title("💶 실시간 유로(EUR) 계산기")
st.write("네이버 금융 기준 실시간 환율을 적용합니다.")

# 1. 입력 받기 (모바일에서 숫자 키패드가 나오도록 number_input 사용)
euro_input = st.number_input("계산할 유로(€)를 입력하세요", min_value=0.0, step=1.0)

# 2. 버튼 및 계산 로직
if st.button("환율 계산하기"):
    with st.spinner('환율 정보를 가져오는 중...'):
        try:
            # 환율 가져오기
            current_rate = get_euro_rate()
            korea_won = euro_input * current_rate
            
            # 잠시 대기 (너무 빨라서 로딩 효과가 안 보일까봐 넣는 UX 요소)
            time.sleep(0.5) 
            
            # 3. 결과 보여주기
            st.success(f"현재 환율: **{current_rate:,.2f}원**")
            st.markdown(f"### 🇰🇷 약 {int(korea_won):,} 원")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# 바닥글
st.caption("Data source: Naver Finance")