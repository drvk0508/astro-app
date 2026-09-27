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
APP_VERSION = "4.1 (Fixed Syntax & Active Gemini Models)"

# Active & Supported Gemini Models (Google GenAI SDK Format)
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
    prompt = f"""Tum ek expert Astro-Vastu research data extraction assistant ho.
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
    prompt = f"""Tum Acharya Vijay Krishna Shastri ke Astro-Vastu research assistant ho.
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
    md.append("# " + str(report.get('report_title', 'एस्ट्रो-वास्तु शोध रिपोर्ट')))
    md.append("\n## कार्यपालक सारांश (Executive Summary)\n" + str(report.get('executive_summary', '')))
    md.append("\n## डेटा गुणवत्ता नोट (Data Quality Note)\n" + str(report.get('data_quality_note', '')))
    md.append("\n## 1. करियर एवं वित्तीय स्थिति (Career & Finance)\n" + str(report.get('career_and_finance_cause', '')))
    md.append("\n## 2. नौकरी एवं ऋण समय-सीमा (Timeline)\n" + str(report.get('job_and_debt_timeline', '')))
    md.append("\n## 3. विवाह एवं नवमांश विश्लेषण (D-9 Analysis)\n" + str(report.get('marriage_d9_analysis', '')))
    md.append("\n## 4. संतान एवं सप्तमांश विश्लेषण (D-7 Analysis)\n" + str(report.get('children_d7_analysis', '')))

    md.append("\n## 5. आगामी 1-वर्ष का त्रैमासिक विवरण (Quarterly Breakdown)\n")
    for q in report.get('quarterly_breakdown', []):
        md.append("### " + str(q.get('quarter', '')) + " — " + str(q.get('period', '')))
        md.append("**करियर (Career):** " + str(q.get('career', '')))
        md.append("**वित्त (Finance):** " + str(q.get('finance', '')))
        md.append("**ऋण (Debt):** " + str(q.get('debt', '')))
        md.append("**संबंध (Relationship):** " + str(q.get('relationship', '')))
        md.append("**गोचर (Important Transits):** " + str(q.get('important_transits', '')))
        md.append("**व्यावहारिक सलाह (Practical Advice):** " + str(q.get('practical_advice', '')) + "\n")

    md.append("## 6. व्यावहारिक वास्तु संशोधन (Vastu Remedies)\n")
    for item in report.get('vastu_improvements', []):
        md.append("- " + str(item))

    md.append("\n## 7. आध्यात्मिक एवं यंत्र उपाय (Spiritual & Yantra Remedies)\n")
    for item in report.get('spiritual_remedies', []):
        md.append("- " + str(item))

    md.append("\n## 8. महत्वपूर्ण तिथियां (Important Dates)\n")
    for item in report.get('important_dates', []):
        md.append("- " + str(item))

    md.append("\n## 9. सीमाएं एवं सावधानियां (Limitations)\n")
    for item in report.get('limitations', []):
        md.append("- " + str(item))

    md.append("\n---\n*यह रिपोर्ट आचार्य विजय कृष्ण शास्त्री एस्ट्रो-वास्तु मार्गदर्शन पद्धति पर आधारित है।*")
    return "\n".join(md)


# ============================================================
# UI HEADER & SIDEBAR AUTH
# ============================================================

st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("आचार्य विजय कृष्ण शास्त्री विशेष फ्रेमवर्क")

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

    if st.button("🚀 Generate Hindi Astro-Vastu Report", type="primary"):
        if not uploaded_file:
            st.error("Please Kundli PDF upload karein.")
            st.stop()

        if not past_events.strip():
            st.error("Please Past Events / Query enter karein.")
            st.stop()

        try:
            client = get_gemini_client()
            pdf_bytes = validate_pdf(uploaded_file)

            with st.spinner("चरण 1/2 — कुंडली से डाटा निकाला जा रहा है..."):
                extraction = extract_kundli_data(client, pdf_bytes, past_events)

            st.success("चरण 1 पूर्ण — कुंडली डेटा सफलतापूर्वक निकाला गया।")

            with st.expander("🔍 View Extracted Kundli Data (JSON)"):
                st.json(extraction)

            with st.spinner("चरण 2/2 — हिंदी एस्ट्रो-वास्तु रिपोर्ट तैयार की जा रही है..."):
                final_report = generate_final_report(client, extraction, past_events)

            st.session_state['extraction_data'] = extraction
            st.session_state['final_report'] = final_report
            st.session_state['chat_history'] = []
            st.success("हिंदी एस्ट्रो-वास्तु रिपोर्ट सफलतापूर्वक तैयार हो गई है!")

        except Exception as e:
            st.error("Report generation failed: " + str(e))

    # ============================================================
    # REPORT DISPLAY & FOLLOW-UP CHAT SECTION
    # ============================================================

    if "final_report" in st.session_state:
        st.markdown("---")
        markdown_report = report_to_markdown(st.session_state['final_report'])
        st.markdown(markdown_report)

        st.download_button(
            label="📥 Download Hindi Report (Markdown)",
            data=markdown_report,
            file_name="Hindi_Astro_Vastu_Report.md",
            mime="text/markdown"
        )

        st.markdown("---")
        st.header("💬 अपनी कुंडली के बारे में सवाल पूछें (Ask Questions)")
        st.write("रिपोर्ट और कुंडली के आधार पर आप नीचे कोई भी प्रश्न हिंदी या Hinglish में पूछ सकते हैं:")

        for msg in st.session_state.get('chat_history', []):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_question = st.chat_input("अपना प्रश्न यहाँ लिखें (उदा: क्या मुझे व्यापार में सफलता मिलेगी?)...")

        if user_question:
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.write(user_question)

            with st.chat_message("assistant"):
                with st.spinner("आचार्य जी विश्लेषण कर रहे हैं..."):
                    try:
                        client = get_gemini_client()
                        kundli_str = json.dumps(st.session_state['extraction_data'], ensure_ascii=False)
                        report_str = json.dumps(st.session_state['final_report'], ensure_ascii=False)
                        
                        chat_prompt = f"""Tum Acharya Vijay Krishna Shastri ke Astro-Vastu assistant ho.
Niche di gayi Kundli Extraction Data aur Report ke aadhar par user ke sawal ka saral, spashth aur accurate uttar HINDI (Devnagri) me do.

KUNDLI DATA:
{kundli_str}

REPORT DATA:
{report_str}

USER QUESTION: {user_question}"""

                        response = call_gemini_with_fallback(
                            client=client,
                            contents=chat_prompt,
                            config=None
                        )

                        answer = response.text if response and response.text else "क्षमा करें, उत्तर प्राप्त नहीं हो सका।"
                        st.write(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})

                    except Exception as chat_err:
                        st.error("Sawal ka uttar dene me error aaya: " + str(chat_err))

else:
    st.info("Report generate karne ke liye sidebar mein valid Student Passcode enter karein.")
