import streamlit as st
from chatbot_core import get_response

st.set_page_config(
    page_title="SwasthyaSathi Chatbot", page_icon="🧠", layout="centered"
)

st.title("🧠 SwasthyaSathi Chatbot")
st.markdown(
    """
Welcome to **SwasthyaSathi** – a hospital assistant chatbot built for the **Odia GenAI Hackathon**.

Ask anything related to patients, beds, doctors, or medicines in **Odia, Hindi, or English**.

#### 💡 Example Queries:
- `kete bed available achhi?`
- `doctor sahu available nuhanti`
- `paracetamol achhi ki?`
- `ramesh kie?`
- `discharge karideba ramesh ku`
"""
)

if "chat" not in st.session_state:
    st.session_state.chat = []

user_input = st.text_input("💬 Enter your query:")

if user_input:
    with st.spinner("🤖 Thinking..."):
        bot_response = get_response(user_input)
        st.session_state.chat.append(("👤 You", user_input))
        st.session_state.chat.append(("🤖 Bot", bot_response))

for role, msg in st.session_state.chat:
    st.markdown(f"**{role}:**", unsafe_allow_html=True)
    st.markdown(msg, unsafe_allow_html=True)
