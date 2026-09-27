import json
import streamlit as st

from google import genai
from google.genai import types

from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Astro-Vastu AI Portal",
    page_icon="🔮",
    layout="centered"
)


# ============================================================
# APP CONSTANTS
# ============================================================

APP_NAME = "Astro-Vastu AI Report Generator"
APP_VERSION = "2.0 (Simple Auth)"

GEMINI_MODEL = "gemini-2.5-flash"
MAX_PDF_SIZE_MB = 50


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        if not api_key:
            raise ValueError("GEMINI_API_KEY empty hai.")

        return genai.Client(api_key=api_key)

    except Exception as e:
        st.error(
            "Gemini API configuration error.\n\n"
            f"Details: {str(e)}"
        )
        st.stop()


client = get_gemini_client()


# ============================================================
# PYDANTIC STRUCTURED DATA MODELS
# ============================================================

class PlanetPosition(BaseModel):
    planet: str = ""
    degree: Optional[str] = ""
    rashi: Optional[str] = ""
    bhava: Optional[str] = ""
    nakshatra: Optional[str] = ""
    pada: Optional[str] = ""
    retrograde: Optional[str] = ""


class DashaPeriod(BaseModel):
    mahadasha: str = ""
    antardasha: str = ""
    pratyantar_dasha: str = ""
    sukshma_dasha: str = ""
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""


class DivisionalChart(BaseModel):
    chart: str = ""
    ascendant: Optional[str] = ""
    important_planets: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)


class AshtakavargaData(BaseModel):
    sixth_house: Optional[str] = ""
    seventh_house: Optional[str] = ""
    tenth_house: Optional[str] = ""
    eleventh_house: Optional[str] = ""


class PastEventVerification(BaseModel):
    event: str = ""
    date_or_age: str = ""
    verification: str = ""
    astrological_reason: str = ""


class KundliExtraction(BaseModel):
    extraction_status: str = ""
    birth_details: dict = Field(default_factory=dict)
    current_dasha: DashaPeriod = Field(default_factory=DashaPeriod)
    planet_positions: List[PlanetPosition] = Field(default_factory=list)
    ashtakavarga: AshtakavargaData = Field(default_factory=AshtakavargaData)
    divisional_charts: List[DivisionalChart] = Field(default_factory=list)
    kp_data_available: bool = False
    kp_observations: List[str] = Field(default_factory=list)
    past_event_verification: List[PastEventVerification] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class QuarterlyAnalysis(BaseModel):
    quarter: str = ""
    period: str = ""
    career: str = ""
    finance: str = ""
    debt: str = ""
    relationship: str = ""
    important_transits: str = ""
    practical_advice: str = ""


class FinalAstroReport(BaseModel):
    report_title: str = ""
    executive_summary: str = ""
    data_quality_note: str = ""
    career_and_finance_cause: str = ""
    job_and_debt_timeline: str = ""
    marriage_d9_analysis: str = ""
    children_d7_analysis: str = ""
    quarterly_breakdown: List[QuarterlyAnalysis] = Field(default_factory=list)
    vastu_improvements: List[str] = Field(default_factory=list)
    spiritual_remedies: List[str] = Field(default_factory=list)
    important_dates: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ============================================================
# SIMPLE AUTHENTICATION VERIFICATION
# ============================================================

def verify_passcode(passcode):
    clean_code = str(passcode).strip()
    if not clean_code:
        return {"valid": False, "message": "Passcode empty hai."}

    # Secrets se simple check
    valid_student_code = st.secrets.get("STUDENT_PASSCODE", "ASTRO2026")
    valid_admin_code = st.secrets.get("ADMIN_PASSCODE", "ADMIN2026")

    if clean_code in [valid_student_code, valid_admin_code]:
        return {"valid": True, "message": "Passcode Verified"}
    else:
        return {"valid": False, "message": "Invalid Passcode!"}


# ============================================================
# PDF VALIDATION
# ============================================================

def validate_pdf(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Kundli PDF upload karein.")

    file_name = uploaded_file.name.lower().strip()
    if not file_name.endswith(".pdf"):
        raise ValueError("Sirf PDF file allowed hai.")

    pdf_bytes = uploaded_file.getvalue()
    if not pdf_bytes:
        raise ValueError("Uploaded PDF empty hai.")

    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        raise ValueError(f"PDF {MAX_PDF_SIZE_MB} MB se chhoti honi chahiye.")

    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("File valid PDF format mein nahi lag rahi.")

    return pdf_bytes


# ============================================================
# STEP 1 — KUNDLI EXTRACTION
# ============================================================

def extract_kundli_data(pdf_bytes, past_events):
    extraction_prompt = f"""
तुम एक विशेषज्ञ Astro-Vastu research data extraction assistant हो।
तुम्हारा काम interpretation से पहले Kundli PDF से उपलब्ध astrological information को STRUCTURED और FACTUAL तरीके से extract करना है।

महत्वपूर्ण नियम:
1. PDF में जो data दिखाई/उपलब्ध हो वही निकालो।
2. कोई ग्रह degree, dasha date, KP sub-lord, bhava या divisional chart position अनुमान से मत बनाओ।
3. यदि कोई data PDF में उपलब्ध नहीं है तो उसे खाली छोड़ो और missing_information में लिखो।
4. "100% accurate" का दावा मत करो।
5. OCR/text ambiguity हो तो warnings में लिखो।
6. KP data तभी उपलब्ध बताओ जब PDF में वास्तविक KP information उपलब्ध हो।
7. Past events को केवल उपलब्ध Kundli data के आधार पर verify करो।
8. Exact date दिखाई नहीं देती तो date invent मत करो।

विशेष रूप से निम्न data निकालो:
A. Birth details (Date, Time, Place)
B. Current Vimshottari Dasha
C. Planet positions (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu, Ascendant)
D. Ashtakavarga (6th, 7th, 10th, 11th house)
E. Divisional charts (D-1, D-9, D-10, D-7)
F. KP data (यदि उपलब्ध हो)
G. Past events verification

Client Past Events:
{past_events}

हर event को separately verify करो (Yes/No/Unclear) और astrological reason दो।

Return ONLY JSON matching the supplied schema.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            extraction_prompt
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": KundliExtraction
        }
    )

    if not response.text:
        raise RuntimeError("Gemini ने Step-1 में कोई response नहीं दिया.")

    try:
        return KundliExtraction.model_validate_json(response.text)
    except ValidationError as e:
        raise RuntimeError("Step-1 JSON validation failed: " + str(e))


# ============================================================
# STEP 2 — FINAL REPORT
# ============================================================

def generate_final_report(extraction, past_events):
    verified_json = extraction.model_dump_json(indent=2, ensure_ascii=False)

    report_prompt = f"""
तुम Acharya Vijay Krishna Shastri के Astro-Vastu research assistant हो।
तुम्हें Step-1 में extracted और structured Kundli data दिया गया है।
तुम्हारा काम उस data के आधार पर एक professional Astro-Vastu research report तैयार करना है।

IMPORTANT:
1. Step-1 data को source-of-truth मानो।
2. यदि कोई information missing है तो उसे invent मत करो।
3. Parashari principles को primary interpretive framework रखो।
4. D-9 को marriage, D-7 को children, D-10 को career analysis के लिए उपयोग करो।
5. Vastu remedies को practical और non-demolition approach में रखो।
6. Yantra remedies को spiritual remedy category में रखो।
7. "अचूक", "100% guaranteed" जैसे claims avoid करो।

CLIENT QUERY:
{past_events}

VERIFIED KUNDLI DATA:
{verified_json}

REPORT STRUCTURE:
1. Executive Summary
2. Career & Financial Situation
3. Job / Career / Debt Timeline
4. Marriage (D-1, D-9)
5. Children (D-1, D-7)
6. Next 1 Year Quarterly Breakdown
7. Practical Vastu Improvements
8. Spiritual / Yantra Remedies
9. Important Dates
10. Limitations

Return ONLY valid JSON matching the supplied schema.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=report_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": FinalAstroReport
        }
    )

    if not response.text:
        raise RuntimeError("Gemini ने Step-2 में कोई response नहीं दिया.")

    try:
        return FinalAstroReport.model_validate_json(response.text)
    except ValidationError as e:
        raise RuntimeError("Step-2 JSON validation failed: " + str(e))


# ============================================================
# MARKDOWN REPORT FORMATTER
# ============================================================

def report_to_markdown(report):
    md = []
    md.append(f"# {report.report_title or 'Astro-Vastu Precision Report'}")
    md.append("\n## Executive Summary\n" + report.executive_summary)
    md.append("\n## Data Quality Note\n" + report.data_quality_note)
    md.append("\n## 1. Career & Financial Situation\n" + report.career_and_finance_cause)
    md.append("\n## 2. Job / Career / Debt Timeline\n" + report.job_and_debt_timeline)
    md.append("\n## 3. Marriage — D-9 Analysis\n" + report.marriage_d9_analysis)
    md.append("\n## 4. Children — D-7 Analysis\n" + report.children_d7_analysis)

    md.append("\n## 5. Upcoming 1-Year Quarterly Breakdown\n")
    for q in report.quarterly_breakdown:
        md.append(f"\n### {q.quarter} — {q.period}\n")
        md.append(f"**Career:** {q.career}\n")
        md.append(f"**Finance:** {q.finance}\n")
        md.append(f"**Debt:** {q.debt}\n")
        md.append(f"**Relationship:** {q.relationship}\n")
        md.append(f"**Important Transits:** {q.important_transits}\n")
        md.append(f"**Practical Advice:** {q.practical_advice}\n")

    md.append("\n## 6. Practical Vastu Improvements\n")
    for item in report.vastu_improvements:
        md.append(f"- {item}")

    md.append("\n## 7. Spiritual / Yantra Remedies\n")
    for item in report.spiritual_remedies:
        md.append(f"- {item}")

    md.append("\n## 8. Important Dates\n")
    for item in report.important_dates:
        md.append(f"- {item}")

    md.append("\n## 9. Limitations\n")
    for item in report.limitations:
        md.append(f"- {item}")

    md.append("\n---\n*This report is an interpretive Astro-Vastu guidance document and should not be treated as a guaranteed prediction.*")
    return "\n".join(md)


# ============================================================
# SESSION STATE
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ============================================================
# HEADER & SIDEBAR AUTH
# ============================================================

st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("Acharya Vijay Krishna Shastri Special Framework")

st.sidebar.header("🔑 Student Authentication")
student_code = st.sidebar.text_input("Enter Student Passcode", type="password")

if student_code:
    verification = verify_passcode(student_code)
    if verification["valid"]:
        st.session_state.authenticated = True
        st.sidebar.success("Passcode Verified")
    else:
        st.session_state.authenticated = False
        st.sidebar.error(verification["message"])


# ============================================================
# MAIN APPLICATION
# ============================================================

if st.session_state.authenticated:
    st.success("Student authentication successful.")

    uploaded_file = st.file_uploader("📄 Upload Kundli PDF", type=["pdf"])
    past_events = st.text_area(
        "📝 Enter Past Events & Main Query",
        height=180,
        placeholder="Example:\n2019 — Job change\n2021 — Financial problem\n\nMain Query: Career, debt and next 1 year."
    )

    generate_button = st.button("🚀 Generate Astro-Vastu Precision Report", type="primary")

    if generate_button:
        if uploaded_file is None:
            st.error("Please Kundli PDF upload karein.")
            st.stop()

        if not past_events.strip():
            st.error("Please Past Events / Query fill karein.")
            st.stop()

        try:
            pdf_bytes = validate_pdf(uploaded_file)
        except Exception as e:
            st.error(f"PDF Error: {str(e)}")
            st.stop()

        try:
            with st.spinner("Step 1/2 — Extracting structured data from Kundli PDF..."):
                extraction = extract_kundli_data(pdf_bytes, past_events)

            st.success("Step 1 completed — Kundli data extracted.")

            with st.expander("🔍 View Extracted Kundli Data"):
                st.json(extraction.model_dump())

            with st.spinner("Step 2/2 — Preparing Astro-Vastu report..."):
                final_report = generate_final_report(extraction, past_events)

            st.success("Astro-Vastu Report Generated Successfully!")

            markdown_report = report_to_markdown(final_report)
            st.markdown(markdown_report)

            st.download_button(
                label="📥 Download Report as Markdown",
                data=markdown_report,
                file_name="Astro_Vastu_Report.md",
                mime="text/markdown"
            )

            json_report = json.dumps(final_report.model_dump(), ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Download Structured Report JSON",
                data=json_report,
                file_name="Astro_Vastu_Report.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")

else:
    st.info("Report generate karne ke liye Student Passcode enter karein.")
