import streamlit as st

st.title("✅ Streamlit Basic Test App")

st.write("Hello! If you see this, your Streamlit Cloud is working fine.")

name = st.text_input("What's your name?")
if name:
    st.success(f"Welcome, {name} 🎉")

number = st.slider("Pick a number", 0, 100, 50)
st.write("You picked:", number)
