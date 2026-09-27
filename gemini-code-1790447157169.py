import json
import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Astro-Vastu AI Portal",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="expanded"
)

APP_NAME = "Astro-Vastu AI Report Generator"
APP_VERSION = "5.0 (Final Integrated)"

# ============================================================
# ACTIVE GEMINI MODELS
# ============================================================

PRIMARY_MODEL = "gemini-3.8-flash"   # ✅ Updated model
FALLBACK_MODEL_1 = "gemini-2.5-pro"
FALLBACK_MODEL_2 = "gemini-2.5-flash"

MAX_PDF_SIZE_MB = 50

# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise Value
