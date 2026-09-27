import json
import streamlit as st

from google import genai
from google.genai import types

# ============================================================
# STREAMLIT CONFIG & MODEL SELECTION
# ============================================================

st.set_page_config(
    page_title="Astro-Vastu AI Portal",
    page_icon="🔮",
    layout="centered"
)

APP_NAME = "Astro-Vastu AI Report Generator"
APP_VERSION = "2.8 (Model Name Fix)"
GEMINI_MODEL = "gemini-3.8-flash"  # <--- Updated model name
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

def generate_final_report(client, extraction, past_events):
    extraction_str = json.dumps(extraction, ensure_ascii=False, indent=2)
    prompt = (
        "Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.\n"
        "Extracted Kundli data ke aadhar par final research report taiyar karo.\n"
        "ONLY VALID JSON RETURN KARO.\n\n"
        "CLIENT QUERY / EVENTS:\n" + str(past_events) + "\n\n"
        "EXTRACTED DATA:\n" + extraction_str + "\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "report_title": "Astro-Vastu Precision Report",\n'
        '  "executive_summary": "...",\n'
        '  "data_quality_note": "...",\n'
        '  "career_and_finance_cause": "...",\n'
        '  "job_and_debt_timeline": "...",\n'
        '  "marriage_d9_analysis": "...",\n'
        '  "children_d7_analysis": "...",\n'
        '  "quarterly_breakdown": [\n'
        "    {\n"
        '      "quarter": "Q1",\n'
        '      "period": "Jan-Mar",\n'
        '      "career": "...",\n'
        '      "finance": "...",\n'
        '      "debt": "...",\n'
        '      "relationship": "...",\n'
        '      "important_transits": "...",\n'
        '      "practical_advice": "..."\n'
        "    }\n"
        "  ],\n"
        '  "vastu_improvements": ["Remedy 1", "Remedy 2"],\n'
        '  "spiritual_remedies": ["Remedy 1", "Remedy 2"],\n'
        '  "important_dates": ["Date 1", "Date 2"],\n'
        '  "limitations": ["Limitation 1"]\n'
        "}\n"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    if not response.text:
        raise RuntimeError("Gemini ne Step-2 me koi response nahi diya.")

    return parse_gemini_json(response.text)


# ============================================================
# MARKDOWN FORMATTER
# ============================================================

def report_to_markdown(report):
    md = []
    md.append(f"# {report.get('report_title', 'Astro-Vastu Precision Report')}")
    md.append("\n## Executive Summary\n" + str(report.get('executive_summary', '')))
    md.append("\n## Data Quality Note\n" + str(report.get('data_quality_note', '')))
    md.append("\n## 1. Career & Financial Situation\n" + str(report.get('career_and_finance_cause', '')))
    md.append("\n## 2. Job / Career / Debt Timeline\n" + str(report.get('job_and_debt_timeline', '')))
    md.append("\n## 3. Marriage — D-9 Analysis\n" + str(report.get('marriage_d9_analysis', '')))
    md.append("\n## 4. Children — D-7 Analysis\n" + str(report.get('children_d7_analysis', '')))

    md.append("\n## 5. Upcoming 1-Year Quarterly Breakdown\n")
    for q in report.get('quarterly_breakdown', []):
        md.append(f"### {q.get('quarter', '')} — {q.get('period', '')}")
        md.append(f"**Career:** {q.get('career', '')}")
        md.append(f"**Finance:** {q.get('finance', '')}")
        md.append(f"**Debt:** {q.get('debt', '')}")
        md.append(f"**Relationship:** {q.get('relationship', '')}")
        md.append(f"**Important Transits:** {q.get('important_transits', '')}")
        md.append(f"**Practical Advice:** {q.get('practical_advice', '')}\n")

    md.append("## 6. Practical Vastu Improvements\n")
    for item in report.get('vastu_improvements', []):
        md.append(f"- {item}")

    md.append("\n## 7. Spiritual / Yantra Remedies\n")
    for item in report.get('spiritual_remedies', []):
        md.append(f"- {item}")

    md.append("\n## 8. Important Dates\n")
    for item in report.get('important_dates', []):
        md.append(f"- {item}")

    md.append("\n## 9. Limitations\n")
    for item in report.get('limitations', []):
        md.append(f"- {item}")

    md.append("\n---\n*This report is an interpretive Astro-Vastu guidance document.*")
    return "\n".join(md)


# ============================================================
# UI HEADER & SIDEBAR AUTH
# ============================================================

st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("Acharya Vijay Krishna Shastri Special Framework")

st.sidebar.header("🔑 Student Authentication")
student_code = st.sidebar.text_input("Enter Student Passcode", type="password")

if student_code:
    if verify_passcode(student_code):
        st.session_state.authenticated = True
        st.sidebar.success("Passcode Verified")
    else:
        st.session_state.authenticated = False
        st.sidebar.error("Invalid Passcode!")


# ============================================================
# MAIN APPLICATION INTERFACE
# ============================================================

if st.session_state.authenticated:
    st.success("Student authentication successful.")

    uploaded_file = st.file_uploader("📄 Upload Kundli PDF", type=["pdf"])
    past_events = st.text_area(
        "📝 Enter Past Events & Main Query",
        height=180,
        placeholder="Example:\nDATE OF MARRIAGE: 11 NOV 1997\nDATE OF BIRTH OF SON: 06 MAY 1999\n\nMain Query: Career and finance outlook."
    )

    if st.button("🚀 Generate Astro-Vastu Precision Report", type="primary"):
        if not uploaded_file:
            st.error("Please Kundli PDF upload karein.")
            st.stop()

        if not past_events.strip():
            st.error("Please Past Events / Query enter karein.")
            st.stop()

        try:
            client = get_gemini_client()
            pdf_bytes = validate_pdf(uploaded_file)

            with st.spinner("Step 1/2 — Extracting structured data from Kundli PDF..."):
                extraction = extract_kundli_data(client, pdf_bytes, past_events)

            st.success("Step 1 completed — Kundli data extracted.")

            with st.expander("🔍 View Extracted Kundli Data"):
                st.json(extraction)

            with st.spinner("Step 2/2 — Preparing Astro-Vastu report..."):
                final_report = generate_final_report(client, extraction, past_events)

            st.success("Astro-Vastu Report Generated Successfully!")

            markdown_report = report_to_markdown(final_report)
            st.markdown(markdown_report)

            st.download_button(
                label="📥 Download Report as Markdown",
                data=markdown_report,
                file_name="Astro_Vastu_Report.md",
                mime="text/markdown"
            )

        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")

else:
    st.info("Report generate karne ke liye sidebar mein valid Student Passcode enter karein.")
