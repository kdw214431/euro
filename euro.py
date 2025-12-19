import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# 탭 이름과 아이콘 설정
st.set_page_config(page_title="만능 환율 계산기", page_icon="💱")

def get_exchange_rate(target_class):
    """
    선택한 통화(class명)에 맞는 환율을 가져옵니다.
    target_class: 'usd', 'eur', 'jpy' 등
    """
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # f-string을 써서 선택한 통화의 CSS 클래스를 동적으로 넣습니다.
    selector = f"#exchangeList a.head.{target_class} > div > span.value"
    rate_text = soup.select_one(selector).text
    
    return float(rate_text.replace(",", ""))

# --- 화면 구성 ---
st.title("💱 실시간 만능 환율 계산기")
st.caption("네이버 금융 고시 환율을 실시간으로 반영합니다.")

# 1. 통화 선택 상자 (Selectbox)
currency_option = st.selectbox(
    "계산할 통화를 선택하세요:",
    ["미국 달러 ($)", "유럽 연합 (€)", "일본 엔 (¥)"]
)

# 선택된 통화에 따라 필요한 정보 세팅 (파이썬 딕셔너리 활용 느낌으로 변수 설정)
if "달러" in currency_option:
    code = "usd"
    symbol = "$"
    is_jpy = False
elif "유럽" in currency_option:
    code = "eur"
    symbol = "€"
    is_jpy = False
else:
    code = "jpy"
    symbol = "¥"
    is_jpy = True # 엔화는 계산법이 다름

# 2. 금액 입력
money_input = st.number_input(f"금액을 입력하세요 ({symbol})", min_value=0.0, step=1.0)

# 3. 계산 버튼
if st.button("한국 돈으로 얼마?"):
    with st.spinner('최신 환율을 가져오는 중...'):
        try:
            # 환율 가져오기
            rate = get_exchange_rate(code)
            
            # 계산 로직 (엔화는 100으로 나눠줘야 함)
            if is_jpy:
                korea_won = money_input * (rate / 100)
                rate_msg = f"{rate:,.2f}원 (100엔 당)"
            else:
                korea_won = money_input * rate
                rate_msg = f"{rate:,.2f}원"
            
            time.sleep(0.3) # 로딩 효과
            
            # 결과 출력
            st.success(f"적용 환율: **{rate_msg}**")
            st.markdown(f"### 🇰🇷 약 {int(korea_won):,} 원")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.markdown("---")
st.caption("Developed by AI Student")