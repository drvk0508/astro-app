import streamlit as st
import openai
import fitz  # PyMuPDF (PDF reading ke liye)

# Page Configuration
st.set_page_config(page_title="Astro-Vastu AI Portal", page_icon="🔮", layout="centered")
import pandas as pd  # Top par import pandas add kar lein

# Aapki Google Sheet ka CSV Export Link (Yahan apni Sheet ID daalein)
SHEET_ID = "1kDZEHjIGpHLnUYKxyQ_ExpO_0od5EanL5cqogO45ZO4/edit?gid=0#gid=0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/https://docs.google.com/spreadsheets/d/1kDZEHjIGpHLnUYKxyQ_ExpO_0od5EanL5cqogO45ZO4/edit?gid=0#gid=0/gviz/tq?tqx=out:csv"

def check_passcode_and_credits(input_code):
    try:
        df = pd.read_csv(CSV_URL)
        # Clean data for exact match
        df['Passcode'] = df['Passcode'].astype(str).str.strip()
        matched = df[df['Passcode'] == input_code.strip()]
        
        if not matched.empty:
            reports_left = int(matched.iloc[0]['Reports_Left'])
            status = str(matched.iloc[0]['Status']).strip()
            if status == "Active" and reports_left > 0:
                return True, reports_left, "Success"
            elif reports_left <= 0:
                return False, 0, "Credits khatam ho gaye hain! Kripya recharge karwayein."
            else:
                return False, 0, "Aapka account inactive hai."
        else:
            return False, 0, "Invalid Passcode!"
    except Exception as e:
        return False, 0, "Google Sheet connect nahi ho pa rahi hai."
st.title("🔮 Astro-Vastu AI Report Generator")
st.subheader("Acharya Vijay Krishna Shastri Special Framework")

# OpenAI API Key & Passcode System
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Sidebar Login
st.sidebar.header("🔑 Student Authentication")
passcode = st.sidebar.text_input("Enter Your Student Passcode", type="password")

# Passcode Verification (Basic Check)
if passcode:
    st.sidebar.success("Passcode Verified!")
    
    # 1. Kundli PDF Upload Section
    uploaded_file = st.file_uploader("Upload Kundli PDF", type=["pdf"])
    
    # 2. Client Details / Past Events Input
    past_events = st.text_area(
        "Enter Past Events & Query",
        placeholder="Marriage Date, Education, Children DOB, Main Query etc."
    )
    
    # 3. Generate Button
    if st.button("Generate Precision Astro-Vastu Report (1 Credit)"):
        if uploaded_file and past_events:
            with st.spinner("Processing Kundli Data & Generating Report..."):
                
                # PDF Text Extraction
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                pdf_text = ""
                for page in doc:
                    pdf_text += page.get_text()
                
                # --- STEP 1 PROMPT (Extraction & Verification) ---
                step1_prompt = f"""
                तुम मेरे एआई रिसर्च असिस्टेंट और "महा-ज्योतिष डेटा एनालिस्ट" हो। मैं Acharya विजय krishna Shastri हूँ (अप्लाइड Vastu साइंटिस्ट)। 

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
                
                response_step1 = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": step1_prompt}]
                )
                step1_output = response_step1.choices[0].message.content
                
                # --- STEP 2 PROMPT (Report Generation) ---
                step2_prompt = f"""
                अब जब कुण्डली का डेटा सत्यापित हो चुका है, तो "विश्व की सबसे प्रामाणिक एवं वैज्ञानिक ज्योतिष रिपोर्ट" तैयार करो।

                सत्यापित डेटा:
                {step1_output}

                मुख्य प्रश्न: JOB SE FREE HOKAR APNA BUSINESS KAB TAK SET HO JAYEGA?
                
                विश्लेषण के नियम:
                1. पराशर और KP सिस्टम प्राथमिक आधार बनाओ।
                2. लाल किताब और वास्तु नियमों को 'उपाय एवं ऊर्जा संतुलन' (Remedies - no metal strips) के लिए लागू करो।
                3. केवल Dasha aur Transit (शनि/गुरु) की सटीक तिथियां बताओ।

                रिपोर्ट संरचना:
                - भाग 1: करियर एवं धन संकट का सटीक कारण
                - भाग 2: नौकरी बहाली एवं कर्ज़ मुक्ति की सटीक टाइमलाइन
                - भाग 3: वैवाहिक (D-9) एवं संतान (D-7) प्रभाव
                - भाग 4: आगामी 1 वर्ष का 4-Quarterly Breakdown (Table)
                - भाग 5: व्यावहारिक वास्तु सुधार
                - भाग 6: अचूक सात्विक महा-उपाय (यंत्र/Yantra सलाह)
                """
                
                response_step2 = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": step2_prompt}]
                )
                final_report = response_step2.choices[0].message.content
                
                # Display Output
                st.success("Report Generated Successfully!")
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
    st.info("Kripya Report generate karne ke liye apna Student Passcode enter karein.")
