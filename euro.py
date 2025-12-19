import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# 페이지 설정
st.set_page_config(page_title="환율 계산기", page_icon="💱")

def get_exchange_rate(target_class):
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    selector = f"#exchangeList a.head.{target_class} > div > span.value"
    rate_text = soup.select_one(selector).text
    return float(rate_text.replace(",", ""))

# --- 화면 구성 ---
st.title("💱 실시간 환율 계산기")

# 1. 통화 선택 (라디오 버튼으로 변경하여 더 직관적으로)
currency = st.radio(
    "통화를 선택해주세요",
    ["🇺🇸 미국 달러 (USD)", "🇪🇺 유럽 연합 (EUR)", "🇯🇵 일본 엔 (JPY)"],
    horizontal=True # 가로로 배치
)

# 선택에 따른 디자인 및 변수 설정
if "미국" in currency:
    code = "usd"
    symbol = "$"
    # 달러 느낌의 초록색 헤더
    st.markdown(f":green[### 🇺🇸 USD 계산 모드]") 
    is_jpy = False
elif "유럽" in currency:
    code = "eur"
    symbol = "€"
    # 유로 느낌의 파란색 헤더
    st.markdown(f":blue[### 🇪🇺 EUR 계산 모드]")
    is_jpy = False
else:
    code = "jpy"
    symbol = "¥"
    # 엔화 느낌의 빨간색 헤더
    st.markdown(f":red[### 🇯🇵 JPY 계산 모드]")
    is_jpy = True

# 2. 금액 입력 (개선된 부분!)
# value=None으로 설정하면 칸이 비어있습니다.
# format="%.2f"를 지우거나 step을 조정하여 입력을 편하게 합니다.
money_input = st.number_input(
    f"금액을 입력하세요 ({symbol})", 
    min_value=0.0, 
    value=None,  # 핵심: 초기값을 없애서 지울 필요 없게 함
    placeholder=f"예: 100", # 빈 칸일 때 흐릿하게 보이는 힌트
    step=1.0
)

# 3. 계산 버튼 및 결과
if st.button("계산하기", type="primary"): # 버튼 색상을 강조(primary)
    if money_input is None:
        st.warning("금액을 입력해주세요!")
    else:
        with st.spinner('환율 정보를 가져오는 중...'):
            try:
                rate = get_exchange_rate(code)
                
                if is_jpy:
                    korea_won = money_input * (rate / 100)
                    rate_msg = f"{rate:,.2f}원 (100엔 당)"
                else:
                    korea_won = money_input * rate
                    rate_msg = f"{rate:,.2f}원"
                
                time.sleep(0.3)
                
                # 결과 디자인 개선 (박스 형태로 깔끔하게)
                st.write("---")
                st.caption(f"적용 환율: {rate_msg}")
                
                # 큰 글씨로 결과 보여주기
                st.markdown(f"### 🇰🇷 한화 약 :blue[{int(korea_won):,} 원]")
                
            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")