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
    layout="centered"
)

APP_NAME = "Astro-Vastu AI Report Generator"
APP_VERSION = "2.3 (UI & Auth Fix)"
GEMINI_MODEL = "gemini-2.5-flash"
MAX_PDF_SIZE_MB = 50


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client():
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY Secrets mein missing hai.")
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Gemini API Config Error: {str(e)}")
        st.stop()

client = get_gemini_client()


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


# Initialize session state for auth
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


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

def extract_kundli_data(pdf_bytes, past_events):
    prompt = f"""
Tum ek expert Astro-Vastu research data extraction assistant ho.
PDF se sabhi astrological details dhyan se extract karo aur NICHE DIYE GAYE FORMAT MEIN STRICT VALID JSON RETURN KARO.

CLIENT PAST EVENTS / QUERY:
{past_events}

Return ONLY valid JSON with this exact structure:
{{
  "extraction_status": "Success / Partial",
  "birth_details": "DOB, Time, Place",
  "current_dasha": {{
    "mahadasha": "",
    "antardasha": "",
    "pratyantar_dasha": "",
    "sukshma_dasha": "",
    "start_date": "",
    "end_date": ""
  }},
  "planet_positions": [
    {{
      "planet": "Sun",
      "degree": "",
      "rashi": "",
      "bhava": "",
      "nakshatra": "",
      "pada": "",
      "retrograde": "Yes/No"
    }}
  ],
  "ashtakavarga": {{
    "sixth_house": "",
    "seventh_house": "",
    "tenth_house": "",
    "eleventh_house": ""
  }},
  "divisional_charts": [
    {{
      "chart": "D-1",
      "ascendant": "",
      "important_planets": [],
      "observations": []
    }}
  ],
  "kp_data_available": false,
  "kp_observations": [],
  "past_event_verification": [
    {{
      "event": "",
      "date_or_age": "",
      "verification": "Yes/No/Unclear",
      "astrological_reason": ""
    }}
  ],
  "missing_information": [],
  "warnings": []
}}
"""

    pdf_part = types.Part.from_bytes(
        data=pdf_bytes,
        mime_type="application/pdf"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[pdf_part, prompt],
        config={"response_mime_type": "application/json"}
    )

    if not response.text:
        raise RuntimeError("Gemini ne Step-1 me koi response nahi diya.")

    return parse_gemini_json(response.text)


# ============================================================
# STEP 2 — FINAL REPORT
# ============================================================

def generate_final_report(extraction, past_events):
    prompt = f"""
Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.
Extracted Kundli data ke aadhar par final research report taiyar karo.
ONLY VALID JSON RETURN KARO.

CLIENT QUERY / EVENTS:
{past_events}

EXTRACTED DATA:
{json.dumps(extraction, ensure_ascii=False, indent=2)}

Return ONLY valid JSON with this exact structure:
{{
  "report_title": "Astro-Vastu Precision Report",
  "executive_summary": "...",
  "data_quality_note": "...",
  "career_and_finance_cause": "...",
  "job_and_debt_timeline": "...",
  "marriage_d9_analysis": "...",
  "children_d7_analysis": "
