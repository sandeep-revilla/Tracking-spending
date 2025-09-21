# app.py
import streamlit as st
import pandas as pd
import time

st.title("🚀 Streamlit Test App")

st.write("If you see this, Streamlit Cloud is working ✅")

# Simple counter
count = st.number_input("Enter a number", min_value=0, max_value=100, value=0)
st.write("You entered:", count)

# Make a tiny dataframe
df = pd.DataFrame({"A": [1, 2, 3], "B": [10, 20, 30]})
st.write("Here is a sample dataframe:")
st.dataframe(df)

# Simulate progress bar
with st.spinner("Simulating work..."):
    time.sleep(2)
st.success("Done!")
