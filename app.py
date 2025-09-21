# test_secret.py
import streamlit as st, json
st.title("Secret test")
try:
    raw = st.secrets["gcp_service_account"]
    st.write("type:", type(raw))
    if isinstance(raw, str):
        st.write("len:", len(raw))
        try:
            parsed = json.loads(raw)
            st.write("Parsed JSON keys:", list(parsed.keys()))
        except Exception as e:
            st.write("json.loads error:", e)
            s2 = raw.replace('\\n', '\n')
            try:
                parsed2 = json.loads(s2)
                st.write("Parsed after \\n replace keys:", list(parsed2.keys()))
            except Exception as e2:
                st.write("second parse error:", e2)
    else:
        st.write("dict keys:", list(raw.keys()))
except Exception as e:
    st.error("st.secrets error: " + str(e))
