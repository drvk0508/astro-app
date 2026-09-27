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
APP_VERSION = "3.3 (Fixed Syntax Error + Fallback + Hindi Devnagri)"

# Stable Models for 2026 API Version
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
    Pehle primary model par try karta hai.
    Agar 404/503/Busy issue aaye, toh active backup models par switch ho jata hai.
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
    prompt = f"""
Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.
Extracted Kundli data ke aadhar par final research report PURE HINDI (DEVNAGRI SCRIPT - देवनागरी) me taiyar karo.
English alphabets ka prayog kewal technical terms ya dates ke liye hi karein. Baaki poora text Hindi (Devnagri) me hona chahiye.
ONLY VALID JSON RETURN KARO.

CLIENT QUERY / EVENTS:
{past_events}

EXTRACTED DATA:
{extraction_str}

Return ONLY valid JSON with this exact structure:
{{
  "report_title": "एस्ट्रो-वास्तु शोध रिपोर्ट",
  "executive_summary": "हिंदी में...",
  "data_quality_note": "हिंदी में...",
  "career_and_finance_cause": "हिंदी में...",
  "job_and_debt_timeline": "हिंदी में...",
  "marriage_d9_analysis": "हिंदी में...",
  "children_d7_analysis": "हिंदी में...",
  "quarterly_breakdown": [
    {{
      "quarter": "Q1",
      "period": "जनवरी - मार्च",
      "career": "हिंदी में...",
      "finance": "हिंदी में...",
      "debt": "हिंदी में...",
      "relationship": "हिंदी में...",
      "important_transits": "हिंदी में...",
      "practical_advice": "हिंदी में..."
    }}
  ],
  "vastu_improvements": ["वास्तु उपाय 1", "वास्तु उपाय 2"],
  "spiritual_remedies": ["यंत्र व आध्यात्मिक उपाय 1", "उपाय 2"],
  "important_dates": ["महत्वपूर्ण तिथि 1", "महत्वपूर्ण तिथि 2"],
  "limitations": ["सीमा 1"]
}}
"""

    response = call_gemini_with_fallback(
        client=client,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    return parse_gemini_json(response.text)


# ============================================================
# MARKDOWN FORMATTER (HINDI)
# ============================================================

def report_to_markdown(report):
    md = []
    md.append(f"# {report.get('report_title', 'एस्ट्रो-वास्तु शोध रिपोर्ट')}")
    md.append("\n## कार्यपालक सारांश (Executive Summary)\n" + str(report.get('executive_summary', '')))
    md.append("\n## डेटा गुणवत्ता नोट (Data Quality Note)\n" + str(report.get('data_quality_note', '')))
    md.append("\n## 1. करियर एवं वित्तीय स्थिति (Career & Finance)\n" + str(report.get('career_and_finance_cause', '')))
    md.append("\n## 2. नौकरी एवं ऋण समय-सीमा (Timeline)\n" + str(report.get('job_and_debt_timeline', '')))
    md.append("\n## 3. विवाह एवं नवमांश विश्लेषण (D-9 Analysis)\n" + str(report.get('marriage_d9_analysis', '')))
    md.append("\n## 4. संतान एवं सप्तमांश विश्लेषण (D-7 Analysis)\n" + str(report.get('children_d7_analysis', '')))

    md.append("\n## 5. आगामी 1-वर्ष का त्रैमासिक विवरण (Quarterly Breakdown)\n")
    for q in report.get('quarterly_breakdown', []):
        md.append(f"### {q.get('quarter', '')} — {q.get('period', '')}")
        md.append(f"**करियर (Career):** {q.get('career', '')}")
        md.append(f"**वित्त (Finance):** {q.get('finance', '')}")
        md.append(f"**ऋण (Debt):** {q.get('debt', '')}")
        md.append(f"**संबंध (Relationship):** {q.get('relationship', '')}")
        md.append(f"**गोचर (Important Transits):** {q.get('important_transits', '')}")
        md.append(f"**व्यावहारिक सलाह (Practical Advice):** {q.get
