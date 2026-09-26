import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from google import genai

st.set_page_config(page_title="Astro-Vastu AI Portal", page_icon="🔮", layout="centered")

# Gemini Client Initialize
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Google Sheet Details
SHEET_ID = "1kDZEHJiGpHLnUYKxyQ_Exp0_0od5EanL5cqog045ZO4"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def check_passcode_and_credits(input_code):
    try:
        df = pd.read_csv(CSV_URL)
        
        # Space remove aur Uppercase conversion
        df['Passcode'] = df['Passcode'].astype(str).str.strip().str.upper()
        clean_code = str(input_code).strip().upper()
        
        matched = df[df['Passcode'] == clean_code]
        
        if not matched.empty:
            reports_left = int(matched.iloc[0]['Reports_Left'])
            status = str(matched.iloc[0]['Status']).strip()
            
            if status.lower() == "active" and reports_left > 0:
                return True, reports_left, "Success"
            elif reports_left <= 0:
                return False, 0, "Credits khatam ho gaye hain!"
            else:
                return False, 0, "Aapka Passcode inactive hai."
        else:
            return False, 0, f"Passcode '{clean_code}' Sheet mein nahi mila."
            
    except Exception as e:
        return False, 0, f"Sheet Read Error: {str(e)}"

st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("Acharya Vijay Krishna Shastri Special Framework")

# Sidebar Authentication
st.sidebar.subheader("🔑 Student Authentication")
student_code = st.sidebar.text_input("Enter Your Student Passcode", type="password")

if student_code:
    is_valid, credits_left, msg = check_passcode_and_credits(student_code)
    
    if is_valid:
        st.sidebar.success(f"Verified! Reports Left: {credits_left}")
        
        uploaded_file = st.file_uploader("Upload Kundli PDF", type=["pdf"])
        past_events = st.text_area("Enter Past Events & Query")
        
        if st.button("Generate Astro-Vastu Precision Report (1 Credit)"):
            if uploaded_file and past_events:
                with st.spinner("Gemini AI Kundli Analysis Kar Raha Hai..."):
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    pdf_text = "".join([page.get_text() for page in doc])
                    
                    # --- STEP 1 PROMPT (Extraction & Verification) ---
                    step1_prompt = f"""
                    तुम मेरे एआई रिसर्च असिस्टेंट और "महा-ज्योतिष डेटा एनालिस्ट" हो। मैं Acharya Vijay Krishna Shastri हूँ (अप्लाइड Vastu साइंटिस्ट)। 

                    अटैच की गई Kundli PDF Data:
                    {pdf_text[:4000]}

                    Client Past Events:
                    {past_events}

                    निम्नलिखित डेटा पॉइंट्स को PDF से 100% सटीकता के साथ निकालकर Table/List में प्रस्तुत करो:
                    1. विंशोत्तरी महादशा, अंतर्दशा, प्रत्यंतर्दशा और सूक्ष्मदशा।
                    2. ग्रह स्थिति (Degrees, Rashi, Bhava, Retrograde).
                    3. अष्टकवर्ग अंक (6th, 7th, 10th, 11th भाव).
                    4. D-1, D-9, D-10, D-7 में प्रमुख ग्रहों की स्थिति।
                    Past Events timeline verification: 'Yes' या 'No' के साथ संक्षिप्त पुष्टि दो।
                    """
                    
                    response_step1 = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=step1_prompt,
                    )
                    step1_output = response_step1.text
                    
                    # --- STEP 2 PROMPT (Report Generation) ---
                    step2_prompt = f"""
                    अब जब कुण्डली का डेटा सत्यापित हो चुका है, तो "विश्व की सबसे प्रामाणिक एवं वैज्ञानिक ज्योतिष रिपोर्ट" तैयार करो।

                    सत्यापित डेटा:
                    {step1_output}

                    मुख्य प्रश्न: {past_events}
                    
                    विश्लेषण के नियम:
                    1. पराशर और KP सिस्टम प्राथमिक आधार बनाओ।
                    2. लाल किताब और वास्तु नियमों को 'उपाय एवं ऊर्जा संतुलन' (Remedies - no metal strips, strictly use Yantra remedies) के लिए लागू करो।
                    3. केवल Dasha aur Transit (शनि/गुरु) की सटीक तिथियां बताओ।

                    रिपोर्ट संरचना:
                    - भाग 1: करियर एवं धन संकट का सटीक कारण
                    - भाग 2: नौकरी बहाली एवं कर्ज़ मुक्ति की सटीक टाइमलाइन
                    - भाग 3: वैवाहिक (D-9) एवं संतान (D-7) प्रभाव
                    - भाग 4: आगामी 1 वर्ष का 4-Quarterly Breakdown (Table)
                    - भाग 5: व्यावहारिक वास्तु सुधार
                    - भाग 6: अचूक सात्विक महा-उपाय (यंत्र/Yantra सलाह)
                    """
                    
                    response_step2 = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=step2_prompt,
                    )
                    final_report = response_step2.text
                    
                    # Display Output
                    st.success("Report Generated Successfully via Gemini AI!")
                    st.markdown(final_report)
                    
                    # Download Button
                    st.download_button(
                        label="📥 Download Report as Text/Markdown",
                        data=final_report,
                        file_name="Astro_Vastu_Report.txt",
                        mime="text/plain"
                    )
            else:
                st.error("Kripya Kundli PDF upload karein aur Past Events fill karein!")
    else:
        st.sidebar.error(msg)
else:
    st.info("Kripya Report generate karne ke liye apna Student Passcode enter karein.")
