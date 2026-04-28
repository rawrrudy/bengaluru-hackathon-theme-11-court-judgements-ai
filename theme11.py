import streamlit as st
import pdfplumber
import re
import pandas as pd
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv("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"))
def extract_info_ai(text):
    prompt = f"""
    You are a legal assistant.

    Extract the following from the court judgment:
    - Case name (Petitioner vs Respondent)
    - Date of judgment
    - Key directions (list of actions)

    Return ONLY valid JSON in this format:

    {{
        "case": "...",
        "date": "...",
        "directions": ["...", "..."]
    }}

    TEXT:
    {text[:4000]}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"case": "Error", "date": "Error", "directions": []}

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="CCMS AI Dashboard", layout="wide")

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚖️ CCMS AI System")
page = st.sidebar.radio("Navigate", ["Upload & Extract", "Review & Verify", "Dashboard"])

# ---------------- PDF TEXT EXTRACTION ----------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# ---------------- INFO EXTRACTION ----------------
def extract_info(text):
    data = {}

    # -------- CLEAN TEXT --------
    text_clean = text.replace("\n", " ")

    # -------- CASE --------
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    petitioner = ""
    respondent = ""

    for i in range(len(lines)):
        if lines[i].lower() == "vs":
            petitioner = lines[i-1]
            respondent = lines[i+1]

            break

  

    #------CLEANUP------
    def clean_name(name):
        name = name.split("…")[0]
        name = re.sub(r"[^A-Za-z\s&]", "", name)
        name = " ".join(name.split())
        return name.title()

    
    petitioner = clean_name(petitioner)
    respondent = clean_name(respondent)

    respondent = respondent.replace("Others", "").strip()

    # FINAL OUTPUT
    if petitioner and respondent:
        data["case"] = f"{petitioner} vs {respondent}"
    else:
        data["case"] = "Not Found"
           
        
        # Detect Respondent line
    # -------- DATE (ROBUST) --------
    text_lower = text_clean.lower()

    dated_match = re.search(r"dated.*?(\d{1,2}.*?\d{4})", text_lower)

    if dated_match:
        raw_date = dated_match.group(1)
        raw_date = raw_date.replace("day of", "")
        raw_date = " ".join(raw_date.split())
        data["date"] = raw_date.strip()
    else:
        data["date"] = "Not Found"

    # -------- DIRECTIONS --------
    keywords = ["directed", "ordered", "shall", "hereby", "must"]
    lines = text.split("\n")

    directions = []
    for line in lines:
        if any(word in line.lower() for word in keywords):
            if len(line.strip()) > 30:
                directions.append(line.strip())

    data["directions"] = directions[:5]

    return data

# ---------------- ACTION PLAN ----------------
def generate_action_plan(data):
    actions = []

    for d in data["directions"]:
        action = {
            "Action": d,
            "Authority": "Unknown",
            "Deadline": "Not specified",
            "Compliance": "Required",
            "Appeal": "Consider",
            "Confidence": "75%",
            "Source": d
        }

        d_lower = d.lower()

        # -------- AUTHORITY DETECTION --------
        if "police" in d_lower:
            action["Authority"] = "Police Department"
        elif "municipal" in d_lower or "corporation" in d_lower:
            action["Authority"] = "Municipal Corporation"
        elif "revenue" in d_lower:
            action["Authority"] = "Revenue Department"

        # -------- DEADLINE DETECTION --------
        deadline_match = re.search(r"\d+\s?days", d_lower)
        if deadline_match:
            action["Deadline"] = deadline_match.group(0)

        actions.append(action)

    return actions

# ---------------- MAIN UI ----------------
uploaded_file = st.file_uploader("Upload Court Judgment PDF", type="pdf")

if uploaded_file:
    text = extract_text_from_pdf(uploaded_file)
    try:
        data = extract_info_ai(text)
    except Exception as e:
        st.warning("⚠️ AI unavailable, using backup extraction")
        data = extract_info(text)
    actions = generate_action_plan(data)
    df = pd.DataFrame(actions)

    # -------- PAGE 1 --------
    if page == "Upload & Extract":
        st.title("📄 Judgment Analysis")

        st.subheader("📌 Case Summary")
        st.markdown(f"""
        - **Case:** {data['case']}
        - **Date:** {data['date']}
        """)

        st.subheader("📄 Extracted Text")
        st.text_area("", text[:1500], height=200)

        st.subheader("📌 Extracted Information")
        st.json(data)

    # -------- PAGE 2 --------
    elif page == "Review & Verify":
        st.title("🧑‍⚖️ Review & Verification")

        st.subheader("⚡ AI Generated Actions")
        edited_df = st.data_editor(df, use_container_width=True)

        st.subheader("📄 View Source of Selected Action")

        if not edited_df.empty:
            selected_index = st.selectbox("Select Action", edited_df.index)

            selected_action = edited_df.loc[selected_index]

            if "Source" in selected_action:
                st.markdown(f"""
                <div style="background-color:#f0f2f6;color:black;padding:12px;border-radius:10px">
                <b>Source:</b><br>{selected_action["Source"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Source not found in data")
            

        if st.button("✅ Approve Verified Actions"):
            st.session_state["approved"] = edited_df
            st.success("Actions Approved Successfully!")

    # -------- PAGE 3 --------
    elif page == "Dashboard":
        st.title("📊 Government Dashboard")

        if "approved" in st.session_state:
            approved_df = st.session_state["approved"]
            def get_urgency(deadline):
                if "days" in str(deadline):
                    days = int(re.search(r"\d+", deadline).group())

                    if days <= 7:
                        return "🔴 Urgent"
                    elif days <= 30:
                        return "🟡 Moderate"
                    else:
                        return "🟢 Low"
                return "⚪ Unknown"
            approved_df["Urgency"] = approved_df["Deadline"].apply(get_urgency)

            # -------- KPI CARDS --------
            col1, col2, col3 = st.columns(3)

            col1.metric("Total Actions", len(approved_df))
            col2.metric("Pending Actions", len(approved_df))
            col3.metric("Departments Involved", approved_df["Authority"].nunique())

            st.subheader("📋 Action Table")
            def highlight_urgency(row):
                if row["Urgency"] == "🔴 Urgent":
                    return ["background-color: #ffcccc"] * len(row)
                elif row["Urgency"] == "🟡 Moderate":
                    return ["background-color: #fff3cd"] * len(row)
                elif row["Urgency"] == "🟢 Low":
                    return ["background-color: #d4edda"] * len(row)
                return [""] * len(row)
            
            st.dataframe(
                approved_df.style.apply(highlight_urgency, axis=1),
                use_container_width=True
            )

        else:
            st.warning("No approved data yet. Please verify actions first.")