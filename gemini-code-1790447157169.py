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
APP_VERSION = "3.2 (Updated Fallback Models + Hindi Devnagri + Chat)"

# Updated Stable Models for 2026 API Version
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
    """
    Pehle primary model (gemini-2.5-flash) par try karta hai.
    Agar 404/503/Busy issue aaye, toh active backup models par automatic switch hota hai.
    """
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
            # Log & try next model directly if model not found or busy
            continue

    raise RuntimeError(f"Sabhi AI models busy hain ya error aaya: {str(last_exception)}")


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
        raise ValueError(f"PDF {MAX_PDF_SIZE_MB} MB se chhoti honi chahiye.")

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
    prompt = (
        "Tum ek expert Astro-Vastu research data extraction assistant ho.\n"
        "PDF se sabhi astrological details dhyan se extract karo aur NICHE DIYE GAYE FORMAT MEIN STRICT VALID JSON RETURN KARO.\n\n"
        "CLIENT PAST EVENTS / QUERY:\n" + str(past_events) + "\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "extraction_status": "Success / Partial",\n'
        '  "birth_details": "DOB, Time, Place",\n'
        '  "current_dasha": {\n'
        '    "mahadasha": "",\n'
        '    "antardasha": "",\n'
        '    "pratyantar_dasha": "",\n'
        '    "sukshma_dasha": "",\n'
        '    "start_date": "",\n'
        '    "end_date": ""\n'
        "  },\n"
        '  "planet_positions": [\n'
        "    {\n"
        '      "planet": "Sun",\n'
        '      "degree": "",\n'
        '      "rashi": "",\n'
        '      "bhava": "",\n'
        '      "nakshatra": "",\n'
        '      "pada": "",\n'
        '      "retrograde": "Yes/No"\n'
        "    }\n"
        "  ],\n"
        '  "ashtakavarga": {\n'
        '    "sixth_house": "",\n'
        '    "seventh_house": "",\n'
        '    "tenth_house": "",\n'
        '    "eleventh_house": ""\n'
        "  },\n"
        '  "divisional_charts": [\n'
        "    {\n"
        '      "chart": "D-1",\n'
        '      "ascendant": "",\n'
        '      "important_planets": [],\n'
        '      "observations": []\n'
        "    }\n"
        "  ],\n"
        '  "kp_data_available": false,\n'
        '  "kp_observations": [],\n'
        '  "past_event_verification": [\n'
        "    {\n"
        '      "event": "",\n'
        '      "date_or_age": "",\n'
        '      "verification": "Yes/No/Unclear",\n'
        '      "astrological_reason": ""\n'
        "    }\n"
        "  ],\n"
        '  "missing_information": [],\n'
        '  "warnings": []\n'
        "}\n"
    )

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
    prompt = (
        "Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.\n"
        "Extracted Kundli data ke aadhar par final research report PURE HINDI (DEVNAGRI SCRIPT - देवनागरी) me taiyar karo.\n"
        "English alphabets ka prayog kewal technical terms ya dates ke liye hi karein. Baaki poora text Hindi (Devnagri) me hona chahiye.\n"
        "ONLY VALID JSON RETURN KARO.\n\n
