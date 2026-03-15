import streamlit as st
import pandas as pd
from app.client import PropertyGuardianClient
from streamlit_mic_recorder import speech_to_text
import extra_streamlit_components as stx
import json

# --- Cookie Manager ---
def get_cookie_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager

cookie_manager = get_cookie_manager()

# --- Configuration ---
st.set_page_config(
    page_title="Property Guardian AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Client (per session to avoid JWT token collision across users) ---
def get_client():
    if "client" not in st.session_state:
        st.session_state.client = PropertyGuardianClient()
    return st.session_state.client

client = get_client()

# --- CSS Overrides ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Georgia:italic&display=swap');
    
    :root {
        --primary-accent: #D97757;
        --emerald-accent: #1dd49a;
        --amber-accent: #f4b545;
        --bg-color: #F9F8F6;
        --sidebar-bg: #F3F1EC;
        --text-color: #1f1d1d;
        --card-bg: #FFFFFF;
        --border-color: #E5E2DC;
    }

    /* Global Typography & Palette */
    html, body, [class*="css"]  {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--text-color);
    }
    
    /* Claude Paper Background */
    .stApp {
        background-color: var(--bg-color);
    }

    /* Stable Grid / Central Column */
    .block-container {
        max-width: 1000px !important;
        padding-top: 4rem !important;
        padding-bottom: 10rem !important;
        margin: 0 auto !important;
    }
    
    /* Global Card/Element Shadows */
    .element-container, .stMarkdown, .stText {
        border-radius: 12px !important;
    }
    
    /* Premium Input Fields */
    .stTextInput input, .stTextArea textarea {
        border-radius: 12px;
        border: 1px solid var(--border-color) !important;
        background-color: var(--card-bg) !important;
        color: var(--text-color) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 0.9rem 1.1rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary-accent) !important;
        box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.1) !important;
    }
    
    /* --- THE CHAT INPUT ENGINEERING (CLAUDE PILL) --- */
    
    .stChatInputContainer {
        padding-bottom: 2.5rem !important;
        background-color: transparent !important;
    }
    
    .stChatInputContainer > div {
        max-width: 850px !important;
        margin: 0 auto !important;
        background-color: transparent !important;
        position: relative !important;
    }
    
    /* The Pill Container */
    [data-testid="stChatInput"] {
        border-radius: 28px !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05) !important;
        background-color: var(--card-bg) !important;
        overflow: hidden !important;
        position: relative !important;
        padding: 4px !important; /* Give some breathing room */
    }
    
    /* Remove internal Streamlit borders/shadows */
    [data-testid="stChatInput"] > div {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--primary-accent) !important;
        box-shadow: 0 12px 40px rgba(217, 119, 87, 0.1) !important;
    }

    [data-testid="stChatInput"] textarea {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        padding: 1.2rem 100px 1.2rem 1.5rem !important; /* Increase right padding for button */
        font-size: 1.05rem !important;
        line-height: 1.5 !important;
        color: var(--text-color) !important;
        min-height: 56px !important;
    }
    
    /* Style the Send Button */
    [data-testid="stChatInput"] button {
        background-color: var(--primary-accent) !important;
        border-radius: 50% !important; 
        position: absolute !important;
        right: 12px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 40px !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 20 !important;
        transition: all 0.2s ease !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(217, 119, 87, 0.2) !important;
        margin: 0 !important;
    }

    [data-testid="stChatInput"] button:hover {
        background-color: #c4664a !important;
        transform: translateY(-50%) scale(1.05) !important;
    }
    
    /* Hide the default focus ring on the inner div if it appears */
    [data-testid="stChatInput"] div:focus-within {
        box-shadow: none !important;
    }
    
    /* --- MESSAGES & CARDS --- */
    
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 1.5rem !important;
        animation: fadeIn 0.4s ease-out;
        background-color: transparent !important;
    }
    
    /* Assistant Message (Gradient Card) */
    .stChatMessage[data-testid="stChatMessageContentAssistant"] {
        background: linear-gradient(120deg, #f6f3ec, #ffffff) !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.02) !important;
        padding: 1.5rem !important;
    }

    /* User Message (Slate Bubble) */
    .stChatMessage[data-testid="stChatMessageContentUser"] {
        background-color: #f0f2f6 !important; /* Soft slate-ish bubble */
        border: 1px solid #e1e4e8 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
        padding: 1rem 1.25rem !important;
        border-radius: 16px 16px 4px 16px !important;
        margin-left: auto !important;
        max-width: 80%;
    }
    
    /* --- SIDEBAR REFINEMENT --- */
    
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-color);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--primary-accent) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* Sidebar Tool Cards */
    .sidebar-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }

    /* Primary "New Chat" button */
    .new-chat-btn button {
        background: linear-gradient(135deg, var(--primary-accent), #e88d6d) !important;
        color: white !important;
        border: none !important;
        padding: 0.8rem 1.5rem !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(217, 119, 87, 0.25) !important;
        transition: all 0.3s ease !important;
    }

    .new-chat-btn button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(217, 119, 87, 0.35) !important;
    }

    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #eefdf5;
        color: var(--emerald-accent);
        border: 1px solid rgba(29, 212, 154, 0.2);
    }

    .status-badge.offline {
        background: #fff5f5;
        color: #ff4b4b;
        border: 1px solid rgba(255, 75, 75, 0.2);
    }

    /* Micro-interactions */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>

""", unsafe_allow_html=True)

# --- State Management ---
# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "chat_session_id" not in st.session_state:
    import uuid
    st.session_state.chat_session_id = str(uuid.uuid4())

# --- Cookie Check (Survival across refresh) ---
if not st.session_state.authenticated:
    saved_session = cookie_manager.get(cookie="property_guardian_session")
    if saved_session:
        try:
            session_data = json.loads(saved_session)
            saved_token = session_data.get("token")
            saved_email = session_data.get("email")
            if saved_token and saved_email:
                st.session_state.authenticated = True
                st.session_state.user_email = saved_email
                st.session_state.client.set_token(saved_token)
        except Exception:
            pass

# --- Authentication Gate ---
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## ✨ Property Guardian AI")
        st.markdown("Please log in or register to continue.")
        
        tab_login, tab_register = st.tabs(["Login", "Register"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if submitted:
                    if not email or not password:
                        st.error("Please fill in both fields.")
                    else:
                        result = client.login(email, password)
                        if result["status"] == "success":
                            st.session_state.authenticated = True
                            st.session_state.user_email = email
                            
                            # Set tokens in a single JSON cookie to avoid key conflicts
                            token = result.get("token") or st.session_state.client._token
                            session_json = json.dumps({"token": token, "email": email})
                            cookie_manager.set("property_guardian_session", session_json, expires_at=None)
                            
                            st.session_state.messages = []
                            st.rerun()
                        else:
                            st.error(result["message"])
        
        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_pass")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if reg_submitted:
                    if not reg_email or not reg_password:
                        st.error("Please fill in all fields.")
                    elif '@' not in reg_email or '.' not in reg_email.split('@')[-1]:
                        st.error("Please enter a valid email address.")
                    elif reg_password != reg_confirm:
                        st.error("Passwords don't match.")
                    else:
                        result = client.register(reg_email, reg_password)
                        if result["status"] == "success":
                            st.success(result["message"])
                        else:
                            st.error(result["message"])
        
        # Connection status
        st.markdown("---")
        if client.health_check():
            st.success("● Backend Online")
        else:
            st.error("● Backend Offline — run `python main.py`")
    
    st.stop()

# --- Authenticated App ---
# --- Sidebar ---
with st.sidebar:
    st.markdown("### ✨ Property Guardian")
    
    # Status Badge
    is_online = client.health_check()
    status_class = "" if is_online else "offline"
    st.markdown(f'<div class="status-badge {status_class}">{"● System Online" if is_online else "○ System Offline"}</div>', unsafe_allow_html=True)

    st.write("")
    # Enhanced New Chat Button
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋ Start New Chat", use_container_width=True):
        st.session_state.messages = []
        import uuid
        st.session_state.chat_session_id = str(uuid.uuid4())
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("---")
    
    # Tool Categories with Cards
    st.markdown("##### 📁 DATA MANAGEMENT")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**Document Ingestion**")
        st.caption("Upload and index legal property deeds for analysis.")
        
        uploaded_files = st.file_uploader("Add PDF files", accept_multiple_files=True, type="pdf", label_visibility="collapsed")
        if uploaded_files:
            if st.button("Process & Index", type="primary", use_container_width=True):
                 with st.spinner("Analyzing chain of title..."):
                    resp = client.ingest_files(uploaded_files)
                    if resp.get("message"):
                        st.toast(f"Success: {resp['message']}", icon="✨")
                    else:
                        st.error("Processing failed.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.write("")
    st.markdown("##### 🛡️ SECURITY TOOLS")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**Fraud Analytics**")
        st.caption("Check for suspicious title transfers or ownership red flags.")
        
        if st.button("🚀 Run Analysis", use_container_width=True):
            with st.status("Performing deep security audit...") as status:
                anomalies = client.check_fraud()
                status.update(label="Audit Complete", state="complete")
                
                if anomalies:
                    msg = f"**⚠️ Fraud Alert**: Found {len(anomalies)} potential anomalies.\n"
                    for a in anomalies:
                        # Use badge styling for risk levels
                        msg += f"- `{a.get('location')}` : **High Risk** ({a.get('reason')})\n"
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                else:
                     st.session_state.messages.append({"role": "assistant", "content": "✅ **System Secure**: No suspicious transaction patterns detected in the indexed records."})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("##### 🛠️ DEVELOPER TOOLS")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**SQL Explorer**")
        st.caption("Execute raw SELECT queries for manual auditing.")
        
        sql_input = st.text_area("Enter SQL Query", height=100, label_visibility="collapsed", placeholder="SELECT * FROM properties LIMIT 5;")
        if st.button("🔍 Run Query", use_container_width=True):
            if sql_input:
                with st.spinner("Executing query..."):
                    results = client.execute_sql(sql_input)
                    if isinstance(results, list):
                        if results:
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"📊 **SQL Results**:\nFound {len(results)} rows.",
                                "df": pd.DataFrame(results)
                            })
                            st.toast(f"Query returned {len(results)} rows.", icon="📊")
                        else:
                            st.info("Query returned no results.")
                    elif isinstance(results, dict) and results.get("status") == "error":
                        st.error(f"SQL Error: {results.get('message')}")
            else:
                st.warning("Please enter a query.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    if st.button("🚪 Logout Session", use_container_width=True, type="secondary"):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.session_state.messages = []
        cookie_manager.delete("property_guardian_token")
        cookie_manager.delete("property_guardian_email")
        if "client" in st.session_state:
            del st.session_state.client
        st.rerun()

    st.markdown("---")
    st.caption("Property Guardian AI v4.0")

# --- Main Chat Interface ---

if len(st.session_state.messages) == 0:
    import html as html_module
    raw_name = st.session_state.user_email.split('@')[0].capitalize() if st.session_state.user_email else "User"
    display_name = html_module.escape(raw_name)
    
    st.markdown(f"""
        <div style="background: white; border: 1px solid #E5E2DC; border-radius: 24px; padding: 3rem 2rem; text-align: center; margin: 2rem 0; box-shadow: 0 10px 40px rgba(0,0,0,0.03);">
            <h1 style="font-family: 'Georgia', serif; font-style: italic; font-weight: 500; color: #1f1d1d; font-size: 2.8rem; margin-bottom: 1rem;">
                Welcome, {display_name}
            </h1>
            <p style="color: #666; font-size: 1.1rem; max-width: 600px; margin: 0 auto 2.5rem auto; line-height: 1.6;">
                Your Property Guardian AI is ready. Upload documents, run deep-chain fraud analytics, or simply start a conversation about your property risk.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Quick start CTAs
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sidebar-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("📂 **Upload Deed**")
        st.caption("Ingest and index property documents.")
        if st.button("Get Started", key="cta_upload", use_container_width=True):
            st.toast("Use the sidebar 'Data Management' card to upload PDF files.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sidebar-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("💬 **Consult AI**")
        st.caption("Ask anything about property regulations.")
        if st.button("Chat Now", key="cta_chat", use_container_width=True):
            st.toast("Type your question in the box below!")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")

# Render existing messages
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    
    avatar = "👤" if msg["role"] == "user" else "✨"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant":
            # Apply AI specialized card styling
            st.markdown(f'<div class="msg-ai">{msg["content"]}</div>', unsafe_allow_html=True)
            if "df" in msg:
                st.dataframe(msg["df"], use_container_width=True)
            if "sources" in msg and msg["sources"]:
                with st.expander("View Chain of Title sources"):
                    for s in msg["sources"]:
                        st.markdown(f"📍 **{s.get('property', 'N/A')}**\n- Transaction: {s.get('seller', 'Unknown')} → {s.get('buyer', 'Unknown')}")
        else:
            # Apply user bubble styling
            st.markdown(f'<div class="msg-user">{msg["content"]}</div>', unsafe_allow_html=True)

# --- Chat Input Pill ---

# Prompt Suggestions (Helper Chips)
if len(st.session_state.messages) > 0:
    st.markdown("""
        <div style="display: flex; gap: 8px; margin-top: 1rem; margin-bottom: 4px; justify-content: center;">
            <span class="status-badge" style="font-size: 10px; cursor: pointer;">"Show latest transfers"</span>
            <span class="status-badge" style="font-size: 10px; cursor: pointer;">"Check fraud status"</span>
        </div>
    """, unsafe_allow_html=True)

# STT Feature
spoken_text = speech_to_text(language='en', start_prompt="Talk to Guardian", stop_prompt="Stop Listening", just_once=True, key='stt_input')

# Chat Input
typed_prompt = st.chat_input("Ask Property Guardian...")
prompt = spoken_text if spoken_text else typed_prompt

if prompt:
    # 1. Append User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 2. Get AI Response
    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()
        with st.spinner("Analyzing property records..."):
            try:
                response = client.chat(prompt, session_id=st.session_state.chat_session_id)
                
                # Handle different response formats
                if isinstance(response, str):
                    answer = response
                elif isinstance(response, dict):
                    answer = response.get("answer", response.get("output", response.get("message", str(response))))
                else:
                    answer = str(response)
                
                message_placeholder.markdown(f'<div class="msg-ai">{answer}</div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun()
            except Exception as e:
                st.error(f"Interaction Error: {str(e)}")
