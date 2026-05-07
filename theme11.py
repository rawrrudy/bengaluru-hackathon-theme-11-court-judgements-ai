import streamlit as st
import pdfplumber
import re
import pandas as pd
import os
from openai import OpenAI
st.set_page_config(page_title="NitiSetuAI", layout="wide")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def universal_simplifier(text):
    prompt = f"""
    You are an intelligent document simplifier.

    The input text can be ANY type:
    - Legal judgement
    - Article
    - Report
    - Notes
    - Government document

    Your job:
    1. Give a SIMPLE summary (easy for a 12-year-old)
    2. Extract key points (bullet list)
    3. Identify document type
    4. Extract important entities (names, dates, orgs if present)
    5. Suggest actionable insights (if applicable)

    Return ONLY valid JSON:

    {{ 
       "type": "...",
       "summary": "...",
       "key_points": ["...", "..."],
       "entities": ["...", "..."],
       "actions": ["...", "..."]

    }}

    TEXT:
    {text[:5000]}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "type": "Unknown",
            "summary": "Could not process document",
            "key_points": [],
            "entities": [],
            "actions": []
        }
    
st.markdown("""
<style>
            
/* 🌑 Main background */
.main {
    background-color: #0e1117;
    color: white;
}
            
/* 🧊 Glassmorphism Cards */
.card {
    background: rgba(17, 25, 40, 0.75);

    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);

    border-radius: 22px;

    padding: 24px;
    margin-bottom: 18px;

    border: 1px solid rgba(255, 255, 255, 0.18);

    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.45),
        inset 0 1px 0 rgba(255,255,255,0.08);

    transition: all 0.3s ease;
}

.card h4 {
    color: #f8fafc;
    margin-bottom: 12px;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

.card p {
    color: #cbd5e1;
    font-size: 16px;
    line-height: 1.6;
}
            
.card:hover {
    transform: translateY(-4px) scale(1.01);

    border: 1px solid rgba(99, 102, 241, 0.7);

    box-shadow:
        0 12px 40px rgba(79, 70, 229, 0.25),
        0 0 20px rgba(79,70,229,0.15);
}
      
/* 🌑 Sidebar background */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-radius: 0 20px 20px 0;
    padding: 10px;
}
            
/* 🔘 Sidebar radio buttons (bubble style) */
div[role="radiogroup"] {
    width: 100%;
}

div[role="radiogroup"] > label {
    width: 100%;
    display: block;
    background-color: #1e293b;
    padding: 14px 16px;
    border-radius: 14px;
    margin-bottom: 10px;
    transition: 0.2s;
}
            
/* 🟢 Hover effect */
div[role="radiogroup"] > label:hover {
    background-color: #334155;
    cursor: pointer;
}
    
/* 🔴 Selected option */
div[role="radiogroup"] > label[data-selected="true"] {
    background-color: #4f46e5 !important;
    color: white !important;
}
            
/* 📦 Main container spacing */
.block-container {
    padding-top: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
            
/* Chat Bot Bubble effect */

.chat-container {
    margin-top: 20px;
}
            
            
/*  Glass bubbles */

.glass-bubble {
    background: rgba(255, 255, 255, 0.06);

    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);

    border: 1px solid rgba(255,255,255,0.1);

    border-radius: 18px;

    padding: 18px 20px;
    margin-bottom: 16px;

    box-shadow:
        0 8px 32px rgba(0,0,0,0.25);

    transition: all 0.25s ease;
}
            
.glass-bubble:hover {
    transform: translateY(-3px);

    border: 1px solid rgba(99,102,241,0.5);

    box-shadow:
        0 12px 32px rgba(79,70,229,0.2);
}
            
html, body, [class*="css"]  {
        font-size: 18px;
    }

    /*  Section headings */                             
    h3 {
        font-size: 34px !important;
        margin-top: 40px !important;
        margin-bottom: 22px !important;
        font-weight: 700 !important;
    }  

    /*  Better list spacing */       

    ul {
        line-height: 2;
        margin-top: 10px;
    }
            
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
st.sidebar.image("logo.png", width=140)
page = st.sidebar.radio("Navigate", ["📄 Upload", "🧑‍⚖️ Review", "📊 Dashboard"])

# ---------------- PDF TEXT EXTRACTION ----------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# ---------------- INFO EXTRACTION ----------------
def extract_info(text):

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Remove broken HTML remnants
    lines = [
        re.sub(r"<.*?>", "", line)
        for line in lines
    ]

    petitioner = ""
    respondent = ""

    # -------- CASE DETECTION --------
    for i in range(len(lines)):

        if lines[i].lower() == "vs":

            if i > 0:
                petitioner = lines[i - 1]

            if i < len(lines) - 1:
                respondent = lines[i + 1]

            break

    case = (
        f"{petitioner} vs {respondent}"
        if petitioner and respondent
        else "Unknown Case"
    )

    # -------- KEY POINTS --------
    key_points = []

    for l in lines:

        if len(l.split()) > 8:

            cleaned_line = re.sub(r"<.*?>", "", l).strip()

            if cleaned_line not in key_points:
                key_points.append(cleaned_line)

    # -------- ACTIONS --------
    action_keywords = [
        "directed",
        "ordered",
        "shall",
        "must",
        "required"
    ]

    actions = []

    for l in lines:

        if any(k in l.lower() for k in action_keywords):

            cleaned_line = re.sub(r"<.*?>", "", l).strip()

            if cleaned_line not in actions:
                actions.append(cleaned_line)

    # -------- SUMMARY --------
    summary_points = key_points[:2]

    clean_summary = ""

    for point in summary_points:
        clean_summary += f"• {point.strip()}\n\n"

    return {

        "type": "Legal Document",

        "summary": (
            f"{case}\n\n{clean_summary}"
            if clean_summary
            else case
        ),

        "key_points": key_points[:5],

        "entities": [
            re.sub(r"<.*?>", "", petitioner),
            re.sub(r"<.*?>", "", respondent)
        ],

        "actions": actions[:5]
    }

# ---------------- ACTION PLAN ----------------
def generate_action_plan(data):
    actions = []

    for d in data.get("actions", []):
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
uploaded_file = st.file_uploader("Upload Document", type=["pdf", "txt"])

from io import BytesIO

use_demo = st.checkbox("✨ Use Demo Document")

if use_demo:
    with open("mock2.pdf", "rb") as f:
        uploaded_file = BytesIO(f.read())
        uploaded_file.name = "mock2.pdf"

data = {}
text = ""
df = pd.DataFrame()

if uploaded_file:
    #  Handle multiple file types
    if str(uploaded_file.name).endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = uploaded_file.read().decode("utf-8")

    #  loading spinner 
    import time

    loading_placeholder = st.empty()
    progress = st.progress(0)
    status = st.empty()

    loading_placeholder.markdown("""
    <div style="text-align:center;padding:20px;">
        <div class="loader"></div>
        <p style="color:#9ca3af;">Initializing AI...</p>
    </div>
                                
    <style>
    .loader {
        border: 4px solid #1f2937;
        border-top: 4px solid #4f46e5;
        border-radius: 50%;
        width: 45px;   
        height: 45px;
        animation: spin 1s linear infinite;
        margin:auto;
    }
                                 
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
                                 
                                              
    </style>
    """, unsafe_allow_html=True)

    for i in range(100):
        progress.progress(i + 1)
        if i < 30:
            status.text("📄 Reading document...")
        elif i < 60:
            status.text("🧠 Understanding content...")
        elif i < 85:
            status.text("⚖️ Extracting insights...")
        else:
            status.text("✨ Finalizing results...")
        time.sleep(0.01)

    try:
        data = universal_simplifier(text)
    except Exception as e:
        st.warning("⚠️ AI unavailable, using backup extraction")
        data = extract_info(text)

    loading_placeholder.empty()
    progress.empty()
    status.empty()

    #  Safer handling 
    actions = generate_action_plan(data) if "actions" in data else []
    df = pd.DataFrame(actions) if actions else pd.DataFrame()

    # -------- PAGE 1 --------
    
if page == "📄 Upload":

    if not uploaded_file:
        st.info("📂 Please upload a document to begin")
        st.stop()

    st.markdown("""
    <div style="margin-top:10px; margin-bottom:30px;">

    <h1 style="
    margin:0;
    font-size:52px;
    font-weight:800;
    color:#6366f1;
    ">
    NitiSetuAI
    </h1>

    <p style="
    margin-top:10px;
    color:#94a3b8;
    font-size:18px;
    font-weight:500;
    ">
    AI-powered document simplification & insight engine
    </p>

    </div>
    """, unsafe_allow_html=True)


    st.markdown("### 📄 Document Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="card">
        <h4>📌 Document Type</h4>
        <p>{data.get('type', 'Unknown')}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card">
        <h4>🧠 Summary</h4>
        <p>{data.get('summary', 'No summary available')}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 💬 AI Conversation")

    with st.chat_message("user"):
        st.write("📄 Please simplify this legal document.")

    with st.chat_message("assistant"):
        st.write(data.get("summary", "No explanation available"))

    st.markdown("<div style='margin-top:40px'></div>", unsafe_allow_html=True)
    st.markdown("### 🔑 Key Points")
    for point in data.get("key_points", []):
        st.markdown(f"""
        <div class="glass-bubble">
            🔹 {point}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:40px'></div>", unsafe_allow_html=True)
    st.markdown("### 🏷️ Important Entities")
    for entity in data.get("entities", []):
        st.markdown(f"""
        <div class="glass-bubble">
            🏷️ {entity}
        </div>
        """, unsafe_allow_html=True)
 
    st.markdown("<div style='margin-top:40px'></div>", unsafe_allow_html=True)    
    st.markdown("### ⚡ Suggested Actions")
    for action in data.get("actions", []):
        st.markdown(f"""
        <div class="glass-bubble">
            ⚡ {action}
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📄 View Raw Text"):
        st.text_area("", text[:2000], height=250)

    # -------- PAGE 2 --------
elif page == "🧑‍⚖️ Review":

    st.title("🧑‍⚖️ Review & Verification")

    st.subheader("⚡ AI Generated Actions")
    edited_df = st.data_editor(df, use_container_width=True)

    st.subheader("📄 View Source of Selected Action")

    if not edited_df.empty:
        selected_index = st.selectbox("Select Action", edited_df.index)
        selected_action = edited_df.loc[selected_index]

        if "Source" in selected_action:

            st.markdown(f"""
            <div class="card">
                <h4>📄 Original Source Text</h4>
                <p>{selected_action["Source"]}</p>
            </div>
             """, unsafe_allow_html=True)
            
        else:
            st.warning("Source not found in data")
                        

    if st.button("✅ Approve Verified Actions"):
        st.session_state["approved"] = edited_df
        st.success("Actions Approved Successfully!")

    # -------- PAGE 3 --------
elif page == "📊 Dashboard":

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

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Actions", len(approved_df))
        col2.metric("Pending Actions", len(approved_df))
        col3.metric("Departments Involved", approved_df["Authority"].nunique())

        st.subheader("📋 Action Table")

        st.dataframe(approved_df, use_container_width=True)

    else:
        st.warning("No approved data yet. Please verify actions first.")