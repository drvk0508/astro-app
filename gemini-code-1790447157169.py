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
APP_VERSION = "5.2 (Final Debug Ready)"

# ============================================================
# ACTIVE GEMINI MODELS
# ============================================================

PRIMARY_MODEL = "gemini-3.6-flash"   # ✅ Updated model
FALLBACK_MODEL_1 = "gemini-3.5-flash"
FALLBACK_MODEL_2 = "gemini-3.1-pro"

MAX_PDF_SIZE_MB = 50

# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing in Streamlit Secrets.")
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
# MULTI-MODEL FALLBACK
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
    raise RuntimeError(f"All Gemini models failed: {str(last_exception)}")

# ============================================================
# PDF VALIDATION
# ============================================================

def validate_pdf(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Upload Kundli PDF.")
    if not uploaded_file.name.lower().endswith(".pdf"):
        raise ValueError("Only PDF files allowed.")
    pdf_bytes = uploaded_file.getvalue()
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise ValueError("Uploaded PDF is empty.")
    if (len(pdf_bytes) / (1024 * 1024)) > MAX_PDF_SIZE_MB:
        raise ValueError("PDF must be under 50 MB.")
    return pdf_bytes

# ============================================================
# JSON PARSER
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
# KUNDLI EXTRACTION
# ============================================================

def extract_kundli_data(client, pdf_bytes, past_events):
    prompt = f"""Tum ek expert Astro-Vastu assistant ho.
PDF se astrological details extract karo aur valid JSON return karo.

CLIENT PAST EVENTS / QUERY:
{past_events}
"""
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    response = call_gemini_with_fallback(
        client=client,
        contents=[pdf_part, prompt],
        config={"response_mime_type": "application/json"}
    )
    return parse_gemini_json(response.text)

# ============================================================
# FINAL REPORT GENERATION
# ============================================================

def generate_final_report(client, extraction, past_events):
    extraction_str = json.dumps(extraction, ensure_ascii=False, indent=2)
    prompt = f"""Tum Acharya Vijay Krishna Shastri ke Astro-Vastu assistant ho.
Extracted Kundli data ke aadhar par final report Hindi (Devanagari) me taiyar karo.
Return ONLY valid JSON.
CLIENT QUERY / EVENTS:
{past_events}
EXTRACTED DATA:
{extraction_str}
"""
    response = call_gemini_with_fallback(
        client=client,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return parse_gemini_json(response.text)

# ============================================================
# MARKDOWN FORMATTER
# ============================================================

def report_to_markdown(report):
    md = []
    md.append("# " + str(report.get('report_title', 'एस्ट्रो-वास्तु शोध रिपोर्ट')))
    md.append("\n## कार्यपालक सारांश\n" + str(report.get('executive_summary', '')))
    md.append("\n## डेटा गुणवत्ता नोट\n" + str(report.get('data_quality_note', '')))
    md.append("\n## करियर एवं वित्तीय स्थिति\n" + str(report.get('career_and_finance_cause', '')))
    md.append("\n## नौकरी एवं ऋण समय-सीमा\n" + str(report.get('job_and_debt_timeline', '')))
    md.append("\n## विवाह एवं नवमांश विश्लेषण\n" + str(report.get('marriage_d9_analysis', '')))
    md.append("\n## संतान एवं सप्तमांश विश्लेषण\n" + str(report.get('children_d7_analysis', '')))
    return "\n".join(md)

# ============================================================
# UI
# ============================================================

st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("आचार्य विजय कृष्ण शास्त्री फ्रेमवर्क")

st.sidebar.header("🔑 Student Authentication")
student_code = st.sidebar.text_input("Enter Student Passcode", type="password")

if student_code:
    if verify_passcode(student_code):
        st.session_state.authenticated = True
        st.sidebar.success("Passcode Verified")
    else:
        st.session_state.authenticated = False
        st.sidebar.error("Invalid Passcode!")

if st.session_state.authenticated:
    st.success("Student authentication successful.")
    uploaded_file = st.file_uploader("📄 Upload Kundli PDF", type=["pdf"])
    past_events = st.text_area("📝 Enter Past Events & Main Query", height=180)

    if st.button("🚀 Generate Hindi Astro-Vastu Report", type="primary"):
        if not uploaded_file:
            st.error("Please upload Kundli PDF.")
        elif not past_events.strip():
            st.error("Please enter Past Events / Query.")
        else:
            try:
                client = get_gemini_client()
                pdf_bytes = validate_pdf(uploaded_file)
                extraction = extract_kundli_data(client, pdf_bytes, past_events)
                report = generate_final_report(client, extraction, past_events)
                st.markdown(report_to_markdown(report))

            except ValueError as ve:
                st.error(f"Validation Error: {str(ve)}")
            except RuntimeError as re:
                st.error(f"Report generation failed: {str(re)}")
            except Exception as e:
                st.error(f"Unexpected Error: {str(e)}")
