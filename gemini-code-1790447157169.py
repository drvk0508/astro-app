import json
import time
import streamlit as st

from google import genai
from google.genai import types

# ============================================================
# STREAMLIT CONFIG & CONSTANTS
# ============================================================

st.set_page_config(
    page_title="Astro-Vastu AI Portal",
    page_icon="🔮",
    layout="centered"
)

APP_NAME = "Astro-Vastu AI Report Generator"
APP_VERSION = "3.4 (Fixed Syntax & f-string Braces + Multi-Model Fallback)"

# Active 2026 Models
PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL_1 = "gemini-2.5-pro"
FALLBACK_MODEL_2 = "gemini-2.0-flash"

MAX_PDF_SIZE_MB = 50


# ============================================================
# GEMINI CLIENT INITIALIZATION
# ============================================================

def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY Streamlit Secrets mein missing hai.")
    return genai.Client(api_key=api_key)


# ============================================================
# AUTHENTICATION
# ============================================================

def verify_passcode(passcode):
    clean_code = str(passcode).strip()
    if not clean_code:
        return False

    valid_student_code = str(st.secrets.get("STUDENT_PASSCODE", "ASTRO2026")).strip()
    valid_admin_code = str(st.secrets.get("ADMIN_PASSCODE", "ADMIN2026")).strip()

    return clean_code in [valid_student_code, valid_admin_code]


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ============================================================
# MULTI-MODEL FALLBACK & RETRY API CALLER
# ============================================================

def call_gemini_with_fallback(client, contents, config):
    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL_1, FALLBACK_MODEL_2]
    last_exception = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            if response and response.text:
                return response
        except Exception as e:
            last_exception = e
            continue

    raise RuntimeError("Sabhi AI models busy hain ya error aaya: " + str(last_exception))


# ============================================================
# PDF VALIDATION
# ============================================================

def validate_pdf(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Kundli PDF upload karein.")

    if not uploaded_file.name.lower().endswith(".pdf"):
        raise ValueError("Sirf PDF file allowed hai.")

    pdf_bytes = uploaded_file.getvalue()
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise ValueError("Uploaded PDF khali hai.")

    if (len(pdf_bytes) / (1024 * 1024)) > MAX_PDF_SIZE_MB:
        raise ValueError("PDF file 50 MB se chhoti honi chahiye.")

    return pdf_bytes


# ============================================================
# HELPER: CLEAN JSON PARSER
# ============================================================

def parse_gemini_json(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


# ============================================================
# STEP 1 — KUNDLI EXTRACTION
# ============================================================

def extract_kundli_data(client, pdf_bytes, past_events):
    prompt = """
Tum ek expert Astro-Vastu research data extraction assistant ho.
PDF se sabhi astrological details dhyan se extract karo aur NICHE DIYE GAYE FORMAT MEIN STRICT VALID JSON RETURN KARO.

CLIENT PAST EVENTS / QUERY:
""" + str(past_events) + """

Return ONLY valid JSON with this exact structure:
{
  "extraction_status": "Success / Partial",
  "birth_details": "DOB, Time, Place",
  "current_dasha": {
    "mahadasha": "",
    "antardasha": "",
    "pratyantar_dasha": "",
    "sukshma_dasha": "",
    "start_date": "",
    "end_date": ""
  },
  "planet_positions": [
    {
      "planet": "Sun",
      "degree": "",
      "rashi": "",
      "bhava": "",
      "nakshatra": "",
      "pada": "",
      "retrograde": "Yes/No"
    }
  ],
  "ashtakavarga": {
    "sixth_house": "",
    "seventh_house": "",
    "tenth_house": "",
    "eleventh_house": ""
  },
  "divisional_charts": [
    {
      "chart": "D-1",
      "ascendant": "",
      "important_planets": [],
      "observations": []
    }
  ],
  "kp_data_available": false,
  "kp_observations": [],
  "past_event_verification": [
    {
      "event": "",
      "date_or_age": "",
      "verification": "Yes/No/Unclear",
      "astrological_reason": ""
    }
  ],
  "missing_information": [],
  "warnings": []
}
"""

    pdf_part = types.Part.from_bytes(
        data=pdf_bytes,
        mime_type="application/pdf"
    )

    response = call_gemini_with_fallback(
        client=client,
        contents=[pdf_part, prompt],
        config={"response_mime_type": "application/json"}
    )

    return parse_gemini_json(response.text)


# ============================================================
# STEP 2 — FINAL HINDI REPORT
# ============================================================

def generate_final_report(client, extraction, past_events):
    extraction_str = json.dumps(extraction, ensure_ascii=False, indent=2)
    prompt = """
Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.
Extracted Kundli data ke aadhar par final research report PURE HINDI (DEVNAGRI SCRIPT - देवनागरी) me taiyar karo.
English alphabets ka prayog kewal technical terms ya dates ke liye hi karein. Baaki poora text Hindi (Devnagri) me hona chahiye.
ONLY VALID JSON RETURN KARO.

CLIENT QUERY / EVENTS:
""" + str(past_events) + """

EXTRACTED DATA:
""" + extraction_str + """

Return ONLY valid JSON with this exact structure:
{
  "report_title": "एस्ट्रो-वास्तु शोध रिपोर्ट",
  "executive_summary": "हिंदी में...",
  "data_quality_note": "हिंदी में...",
  "career_and_finance_cause": "हिंदी में...",
  "job_and_debt_timeline": "हिंदी में...",
  "marriage_d9_analysis": "हिंदी में...",
  "children_d7_analysis": "हिंदी में...",
