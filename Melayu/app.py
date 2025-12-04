import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os
from dotenv import load_dotenv

# =========================================
# PAGE SETUP
# =========================================
st.set_page_config(
    page_title="🦐 Shrimp Farm Financial Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🦐 Shrimp Farm Performance Dashboard")
st.caption("v1.0 - Analisis Keuangan & Produktivitas Tambak Udang")

# =========================================
# LOAD API (Optional GROQ)
# =========================================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
else:
    client = None

# =========================================
# AI Commentary Function
# =========================================
def generate_ai_commentary(summary_df: pd.DataFrame) -> str:
    """Analisis AI terhadap performa tambak"""
    if not client:
        return "⚠️ AI Commentary tidak aktif (API Key belum diatur)."

    text_summary = summary_df.to_string(index=False)
    prompt = f"""
    Berikut data hasil produksi tambak udang:
    {text_summary}

    Buat analisis singkat dalam bahasa Indonesia:
    - Tambak mana yang paling efisien
    - Tambak mana yang butuh perhatian
    - Insight strategis singkat
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error AI Commentary: {e}"

# =========================================
# DATA UPLOAD
# =========================================
uploaded_file = st.file_uploader("📂 Upload data keuangan tambak (Excel/CSV)", type=["xlsx", "xls", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📜 Data Preview")
    st.dataframe(df.head())

    # =========================================
    # DASHBOARD
    # =========================================
    st.subheader("📈 Analisis Produksi & Keuangan")

    if {"Tambak", "Produksi_kg", "Biaya", "Pendapatan"}.issubset(df.columns):
        query = """
        SELECT 
            Tambak,
            SUM(Produksi_kg) AS Total_Produksi,
            SUM(Biaya) AS Total_Biaya,
            SUM(Pendapatan) AS Total_Pendapatan,
            SUM(Pendapatan) - SUM(Biaya) AS Laba_Bersih
        FROM df
        GROUP BY Tambak
        ORDER BY Laba_Bersih DESC
        """
        summary = duckdb.sql(query).df()

        # Grafik laba bersih per tambak
        fig = px.bar(summary, x="Tambak", y="Laba_Bersih", 
                     title="Laba Bersih per Tambak", text_auto=True,
                     color="Laba_Bersih", color_continuous_scale="Viridis")
        st.plotly_chart(fig, use_container_width=True)

        # =========================================
        # RULE-BASED COMMENTARY
        # =========================================
        st.subheader("📝 Analisis Otomatis (Rule-based)")

        top = summary.iloc[0]
        bottom = summary.iloc[-1]
        commentary = f"""
        🔍 **Insights:**
        - Tambak paling menguntungkan: **{top['Tambak']}** dengan laba **Rp {top['Laba_Bersih']:,.0f}**.
        - Tambak dengan laba terendah: **{bottom['Tambak']}** dengan laba **Rp {bottom['Laba_Bersih']:,.0f}**.
        - Selisih laba antara keduanya: **Rp {(top['Laba_Bersih'] - bottom['Laba_Bersih']):,.0f}**.
        """
        st.markdown(commentary)

        # =========================================
        # AI COMMENTARY
        # =========================================
        st.subheader("🤖 AI Commentary")
        ai_text = generate_ai_commentary(summary)
        st.write(ai_text)

        # =========================================
        # AI CHAT MODE
        # =========================================
        st.subheader("💬 Chat dengan AI Konsultan Tambak")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "system", "content": "Anda adalah konsultan tambak udang yang menganalisis data keuangan dan produksi."},
                {"role": "assistant", "content": ai_text}
            ]

        for msg in st.session_state.chat_history:
            st.chat_message(msg["role"]).write(msg["content"])

        if question := st.chat_input("Tanyakan tentang performa tambak..."):
            st.session_state.chat_history.append({"role": "user", "content": question})
            st.chat_message("user").write(question)

            if client:
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=st.session_state.chat_history,
                        temperature=0.7
                    )
                    answer = response.choices[0].message.content
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    st.chat_message("assistant").write(answer)
                except Exception as e:
                    st.error(f"❌ Error chat: {e}")
            else:
                st.warning("AI chat tidak aktif — tambahkan GROQ_API_KEY di .env")

    else:
        st.warning("⚠️ Pastikan kolom data Anda berisi: Tambak, Produksi_kg, Biaya, Pendapatan")
else:
    st.info("⬆️ Upload file Excel/CSV untuk memulai analisis.")
