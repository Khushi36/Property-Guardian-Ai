import json

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
from streamlit_mic_recorder import speech_to_text
from streamlit_agraph import agraph, Node, Edge, Config

from app.client import PropertyGuardianClient


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
st.markdown(
    """
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

""",
    unsafe_allow_html=True,
)

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
if "graph_mode" not in st.session_state:
    st.session_state.graph_mode = None   # None | "chain" | "network"
if "graph_data_panel" not in st.session_state:
    st.session_state.graph_data_panel = None
if "graph_title" not in st.session_state:
    st.session_state.graph_title = ""

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
                submitted = st.form_submit_button(
                    "Log In", type="primary", use_container_width=True
                )

                if submitted:
                    if not email or not password:
                        st.error("Please fill in both fields.")
                    else:
                        result = client.login(email, password)
                        if result["status"] == "success":
                            st.session_state.authenticated = True
                            st.session_state.user_email = email

                            # Set tokens in a single JSON cookie to avoid key conflicts
                            token = (
                                result.get("token") or st.session_state.client._token
                            )
                            session_json = json.dumps({"token": token, "email": email})
                            cookie_manager.set(
                                "property_guardian_session",
                                session_json,
                                expires_at=None,
                            )

                            st.session_state.messages = []
                            st.rerun()
                        else:
                            st.error(result["message"])

        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input(
                    "Email", placeholder="you@example.com", key="reg_email"
                )
                reg_password = st.text_input(
                    "Password", type="password", key="reg_pass"
                )
                reg_confirm = st.text_input(
                    "Confirm Password", type="password", key="reg_confirm"
                )
                reg_submitted = st.form_submit_button(
                    "Create Account", use_container_width=True
                )

                if reg_submitted:
                    if not reg_email or not reg_password:
                        st.error("Please fill in all fields.")
                    elif "@" not in reg_email or "." not in reg_email.split("@")[-1]:
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
    st.markdown(
        f'<div class="status-badge {status_class}">{"● System Online" if is_online else "○ System Offline"}</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    # Enhanced New Chat Button
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋ Start New Chat", use_container_width=True):
        st.session_state.messages = []
        import uuid

        st.session_state.chat_session_id = str(uuid.uuid4())
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("---")

    # Tool Categories with Cards
    st.markdown("##### 📁 DATA MANAGEMENT")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**Document Ingestion**")
        st.caption("Upload and index legal property deeds for analysis.")

        uploaded_files = st.file_uploader(
            "Add PDF files",
            accept_multiple_files=True,
            type="pdf",
            label_visibility="collapsed",
        )
        if uploaded_files:
            if st.button("Process & Index", type="primary", use_container_width=True):
                with st.spinner("Analyzing chain of title..."):
                    resp = client.ingest_files(uploaded_files)
                    if resp.get("message"):
                        msg = resp["message"]
                        st.toast(f"Success: {msg}", icon="✨")

                        # Extract property IDs from the response message
                        # Format: "file.pdf (Property ID: 3, Plot: 45)"
                        import re as _re
                        prop_ids = _re.findall(r"Property ID:\s*(\d+)", msg)

                        if prop_ids:
                            first_pid = int(prop_ids[0])
                            # Auto-sync to Neo4j so the graph is fresh
                            with st.spinner(f"Syncing Property {first_pid} to Neo4j graph..."):
                                client.sync_neo4j()
                            # Auto-load chain of title for the first ingested property
                            data = client.get_graph_chain(first_pid)
                            chain = data.get("chain", [])
                            if chain:
                                st.session_state.graph_mode = "chain"
                                st.session_state.graph_data_panel = chain
                                st.session_state.graph_title = f"Chain of Title — Property {first_pid}"
                                # Also add a helpful chat message
                                ids_str = ", ".join(prop_ids)
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": (
                                        f"✅ **Document ingested successfully!**\n\n"
                                        f"**Property ID(s):** `{ids_str}`\n\n"
                                        f"The graph below shows the chain of title for **Property {first_pid}**. "
                                        f"You can also search for this ID anytime in the **Graph Explorer** panel on the sidebar."
                                    ),
                                })
                                st.rerun()
                            else:
                                # Graph data not available yet — still show the IDs
                                ids_str = ", ".join(prop_ids)
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": (
                                        f"✅ **Document ingested successfully!**\n\n"
                                        f"**Property ID(s):** `{ids_str}`\n\n"
                                        f"Use these IDs in the **Graph Explorer** → **Chain of Title** to view the ownership graph."
                                    ),
                                })
                                st.rerun()
                    else:
                        st.error("Processing failed.")
        st.markdown("</div>", unsafe_allow_html=True)

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
                    st.session_state.messages.append(
                        {"role": "assistant", "content": msg}
                    )
                else:
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": "✅ **System Secure**: No suspicious transaction patterns detected in the indexed records.",
                        }
                    )
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("##### 🛠️ DEVELOPER TOOLS")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**SQL Explorer**")
        st.caption("Execute raw SELECT queries for manual auditing.")

        sql_input = st.text_area(
            "Enter SQL Query",
            height=100,
            label_visibility="collapsed",
            placeholder="SELECT * FROM properties LIMIT 5;",
        )
        if st.button("🔍 Run Query", use_container_width=True):
            if sql_input:
                with st.spinner("Executing query..."):
                    results = client.execute_sql(sql_input)
                    if isinstance(results, list):
                        if results:
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": f"📊 **SQL Results**:\nFound {len(results)} rows.",
                                    "df": pd.DataFrame(results),
                                }
                            )
                            st.toast(f"Query returned {len(results)} rows.", icon="📊")
                        else:
                            st.info("Query returned no results.")
                    elif isinstance(results, dict) and results.get("status") == "error":
                        st.error(f"SQL Error: {results.get('message')}")
            else:
                st.warning("Please enter a query.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("##### 🕸️ GRAPH EXPLORER")
    with st.container():
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.markdown("**Neo4j Visualization**")
        st.caption("Explore ownership chains and transaction networks.")

        # Sync button
        if st.button("🔄 Sync to Neo4j", use_container_width=True):
            with st.spinner("Syncing data to Neo4j..."):
                result = client.sync_neo4j()
                if result.get("status") in ("completed", "success"):
                    n = result.get("nodes_created", 0)
                    r = result.get("rels_created", 0)
                    st.toast(f"✅ Synced! {n} nodes, {r} relationships", icon="🕸️")
                else:
                    st.error(result.get("message", "Sync failed. Is Neo4j running?"))

        st.write("")

        # Chain of Title by Property ID
        graph_pid = st.number_input(
            "Property ID",
            min_value=1,
            step=1,
            value=1,
            label_visibility="collapsed",
        )
        if st.button("🔗 Chain of Title", use_container_width=True):
            with st.spinner(f"Fetching graph for property {graph_pid}..."):
                data = client.get_graph_chain(int(graph_pid))
                chain = data.get("chain", [])
                if chain:
                    st.session_state.graph_mode = "chain"
                    st.session_state.graph_data_panel = chain
                    st.session_state.graph_title = f"Chain of Title — Property {graph_pid}"
                    st.rerun()
                else:
                    st.warning(f"No graph data found for Property {graph_pid}. Try syncing first.")

        st.write("")

        # Full Network
        if st.button("🌐 Full Network", use_container_width=True):
            with st.spinner("Loading full transaction network..."):
                network = client.get_graph_network()
                if network.get("nodes"):
                    st.session_state.graph_mode = "network"
                    st.session_state.graph_data_panel = network
                    st.session_state.graph_title = f"Full Transaction Network — {len(network['nodes'])} nodes"
                    st.rerun()
                else:
                    st.warning("No network data found. Try syncing to Neo4j first.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    if st.button("🚪 Logout Session", use_container_width=True, type="secondary"):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.session_state.messages = []
        cookie_manager.delete("property_guardian_session")
        if "client" in st.session_state:
            del st.session_state.client
        st.rerun()

    st.markdown("---")
    st.caption("Property Guardian AI v4.0")


# --- Shared graph-rendering helper ---
def render_graph(graph_records, mode="chain", height=500):
    """
    Render an agraph from either:
    - chain mode: list of {seller, buyer, date, txn_id, plot, village}
    - network mode: {nodes: [...], edges: [...]}
    Returns (nodes_count, edges_count).
    """
    COLOR_MAP = {
        "seller": "#D97757",      # Coral — sellers
        "buyer": "#1E90FF",       # Dodger blue — buyers
        "property": "#1dd49a",    # Emerald — properties
        "transaction": "#f4b545", # Amber — transactions
        "document": "#a855f7",    # Purple — documents
    }
    AVATAR = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
    PROP_ICON = "https://cdn-icons-png.flaticon.com/512/602/602175.png"
    TXN_ICON = "https://cdn-icons-png.flaticon.com/512/2921/2921222.png"
    DOC_ICON = "https://cdn-icons-png.flaticon.com/512/2956/2956744.png"

    nodes_list = []
    edges_list = []
    nodes_set = set()

    def add_node(nid, label, ntype, metadata=None):
        if nid not in nodes_set:
            color = COLOR_MAP.get(ntype, "#888")
            icon = AVATAR if ntype in ("seller", "buyer") else (
                PROP_ICON if ntype == "property" else (DOC_ICON if ntype == "document" else TXN_ICON)
            )
            
            # Enrich title with metadata for tooltips
            title = f"{ntype.capitalize()}: {label}"
            if metadata:
                if metadata.get("pan") and metadata["pan"] != "N/A":
                    title += f"\nPAN: {metadata['pan']}"
                if metadata.get("aadhaar") and metadata["aadhaar"] != "N/A":
                    title += f"\nAadhaar: {metadata['aadhaar']}"

            nodes_list.append(
                Node(
                    id=str(nid),
                    label=str(label),
                    title=title,
                    size=28 if ntype in ("seller", "buyer") else 22,
                    shape="circularImage",
                    image=icon,
                    color=color,
                    font={"color": "#1f1d1d", "size": 11, "face": "Plus Jakarta Sans"},
                    borderWidth=2,
                    borderWidthSelected=4,
                )
            )
            nodes_set.add(nid)

    if mode == "chain" and isinstance(graph_records, list):
        for rec in graph_records:
            seller = rec.get("seller") or "Unknown Seller"
            buyer = rec.get("buyer") or "Unknown Buyer"
            date = rec.get("date", "") or "N/A"
            txn_id = rec.get("txn_id", "unknown")
            village = rec.get("village", "") or "Unknown"
            plot = rec.get("plot", "") or "N/A"

            # Use STABLE IDs from backend if possible
            s_key = f"person_{rec.get('seller_id')}" if rec.get("seller_id") else f"person_s_{seller}"
            b_key = f"person_{rec.get('buyer_id')}" if rec.get("buyer_id") else f"person_b_{buyer}"
            t_key = f"txn_{txn_id}"
            p_key = f"prop_{rec.get('prop_id')}" if rec.get("prop_id") else f"prop_{village}_{plot}"

            add_node(s_key, seller, "seller", metadata={"pan": rec.get("seller_pan"), "aadhaar": rec.get("seller_aadhaar")})
            add_node(b_key, buyer, "buyer", metadata={"pan": rec.get("buyer_pan"), "aadhaar": rec.get("buyer_aadhaar")})
            add_node(t_key, f"Sale\n{str(date)[:10]}", "transaction")
            
            p_label = f"Plot {plot}\n{village}"
            add_node(p_key, p_label, "property")

            edges_list.append(Edge(source=s_key, target=t_key, label="SOLD", color="#D97757", width=2, type="CURVE_SMOOTH"))
            edges_list.append(Edge(source=t_key, target=b_key, label="BOUGHT", color="#1E90FF", width=2, type="CURVE_SMOOTH"))
            edges_list.append(Edge(source=t_key, target=p_key, label="FOR", color="#1dd49a", width=1, dashes=True, type="CURVE_SMOOTH"))

            if rec.get("doc_id") is not None:
                d_key = f"doc_{rec['doc_id']}"
                filename = rec["doc_path"].split("/")[-1].split("\\")[-1] if rec.get("doc_path") else f"Doc {rec['doc_id']}"
                add_node(d_key, filename, "document")
                edges_list.append(Edge(source=t_key, target=d_key, label="BASED_ON", color="#a855f7", width=1, type="CURVE_SMOOTH"))

    elif mode == "network" and isinstance(graph_records, dict):
        for n in graph_records.get("nodes", []):
            add_node(n["id"], n["label"], n["type"], metadata=n)
        for e in graph_records.get("edges", []):
            edge_color = "#D97757" if e["label"] == "SOLD" else (
                "#1E90FF" if e["label"] == "BOUGHT_BY" else (
                    "#1dd49a" if e["label"] == "FOR_PROPERTY" else (
                        "#ef4444" if e["label"] == "CROSS_MATCH_WITH" else "#a855f7"
                    )
                )
            )
            dashes = True if e["label"] == "CROSS_MATCH_WITH" else False
            edges_list.append(Edge(
                source=e["source"],
                target=e["target"],
                label=e["label"],
                color=edge_color,
                width=3 if e["label"] == "CROSS_MATCH_WITH" else 2,
                type="CURVE_SMOOTH",
                dashes=dashes,
            ))

    config = Config(
        width="100%",
        height=height,
        directed=True,
        nodeHighlightBehavior=True,
        highlightColor="#D97757",
        collapsible=False,
        physics={"enabled": True, "stabilization": {"iterations": 150}},
        link={"highlightColor": "#D97757", "renderLabel": True},
    )

    if nodes_list and edges_list:
        agraph(nodes=nodes_list, edges=edges_list, config=config)
        return len(nodes_list), len(edges_list)
    elif nodes_list:
        agraph(nodes=nodes_list, edges=[], config=config)
        return len(nodes_list), 0
    return 0, 0

# --- Main Chat Interface ---

# ── Graph Explorer Panel (full-width, rendered before chat) ──────────────
if st.session_state.graph_mode and st.session_state.graph_data_panel is not None:
    gdata = st.session_state.graph_data_panel

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #f6f3ec, #ffffff);
                    border: 1px solid #E5E2DC; border-radius: 20px;
                    padding: 1.5rem 1.75rem; margin-bottom: 1.5rem;
                    box-shadow: 0 8px 30px rgba(0,0,0,0.04);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.75rem;">
            <h3 style="margin:0; font-size:1.1rem; color:#1f1d1d;">🕸️ {st.session_state.graph_title}</h3>
            <div style="display:flex; gap: 10px;">
              <span style="background:#fff3ef; color:#D97757; border:1px solid rgba(217,119,87,0.2); border-radius:20px; padding:3px 10px; font-size:0.72rem; font-weight:600;">● Sellers</span>
              <span style="background:#eff6ff; color:#1E90FF; border:1px solid rgba(30,144,255,0.2); border-radius:20px; padding:3px 10px; font-size:0.72rem; font-weight:600;">● Buyers</span>
              <span style="background:#eefdf5; color:#1dd49a; border:1px solid rgba(29,212,154,0.2); border-radius:20px; padding:3px 10px; font-size:0.72rem; font-weight:600;">● Properties</span>
              <span style="background:#fffbef; color:#f4b545; border:1px solid rgba(244,181,69,0.2); border-radius:20px; padding:3px 10px; font-size:0.72rem; font-weight:600;">● Transactions</span>
              <span style="background:#f3e8ff; color:#a855f7; border:1px solid rgba(168,85,247,0.2); border-radius:20px; padding:3px 10px; font-size:0.72rem; font-weight:600;">● Documents</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode = st.session_state.graph_mode
    n_count, e_count = render_graph(gdata, mode=mode, height=550)

    # Stats bar + clear button
    col_stat1, col_stat2, col_stat3, col_clear = st.columns([1, 1, 1, 1])
    with col_stat1:
        st.metric("Nodes", n_count)
    with col_stat2:
        st.metric("Edges", e_count)
    with col_stat3:
        depth = len(gdata) if isinstance(gdata, list) else len(gdata.get("edges", []))
        st.metric("Records", depth)
    with col_clear:
        if st.button("✖ Close Graph", use_container_width=True):
            st.session_state.graph_mode = None
            st.session_state.graph_data_panel = None
            st.session_state.graph_title = ""
            st.rerun()

    st.markdown("---")


if len(st.session_state.messages) == 0:
    import html as html_module

    raw_name = (
        st.session_state.user_email.split("@")[0].capitalize()
        if st.session_state.user_email
        else "User"
    )
    display_name = html_module.escape(raw_name)

    st.markdown(
        f"""
        <div style="background: white; border: 1px solid #E5E2DC; border-radius: 24px; padding: 3rem 2rem; text-align: center; margin: 2rem 0; box-shadow: 0 10px 40px rgba(0,0,0,0.03);">
            <h1 style="font-family: 'Georgia', serif; font-style: italic; font-weight: 500; color: #1f1d1d; font-size: 2.8rem; margin-bottom: 1rem;">
                Welcome, {display_name}
            </h1>
            <p style="color: #666; font-size: 1.1rem; max-width: 600px; margin: 0 auto 2.5rem auto; line-height: 1.6;">
                Your Property Guardian AI is ready. Upload documents, run deep-chain fraud analytics, or simply start a conversation about your property risk.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Quick start CTAs
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="sidebar-card" style="height: 100%;">', unsafe_allow_html=True
        )
        st.markdown("📂 **Upload Deed**")
        st.caption("Ingest and index property documents.")
        if st.button("Get Started", key="cta_upload", use_container_width=True):
            st.toast("Use the sidebar 'Data Management' card to upload PDF files.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(
            '<div class="sidebar-card" style="height: 100%;">', unsafe_allow_html=True
        )
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
            st.markdown(msg["content"])
            if "df" in msg:
                df = pd.DataFrame(msg["df"])
                if msg.get("chart_type") == "bar" and not df.empty:
                    st.write("📊 **Anomaly Distribution by Village**")
                    # Simple bar chart logic: count anomalies by location if possible
                    chart_data = df.groupby("Location").size().reset_index(name="Count")
                    st.bar_chart(chart_data, x="Location", y="Count")
                else:
                    st.dataframe(df, use_container_width=True)
            if "graph_data" in msg and msg["graph_data"]:
                st.write("🕸️ **Property Chain of Title**")
                render_graph(msg["graph_data"], mode="chain", height=400)

            if "sources" in msg and msg["sources"]:
                with st.expander("View Chain of Title sources"):
                    for s in msg["sources"]:
                        st.markdown(
                            f"📍 **{s.get('property', 'N/A')}**\n- Transaction: {s.get('seller', 'Unknown')} → {s.get('buyer', 'Unknown')}"
                        )
        else:
            st.markdown(msg["content"])

# --- Chat Input Pill ---

# Prompt Suggestions (Helper Chips)
if len(st.session_state.messages) > 0:
    st.markdown(
        """
        <div style="display: flex; gap: 8px; margin-top: 1rem; margin-bottom: 4px; justify-content: center;">
            <span class="status-badge" style="font-size: 10px; cursor: pointer;">"Show latest transfers"</span>
            <span class="status-badge" style="font-size: 10px; cursor: pointer;">"Check fraud status"</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

# STT Feature
spoken_text = speech_to_text(
    language="en",
    start_prompt="Talk to Guardian",
    stop_prompt="Stop Listening",
    just_once=True,
    key="stt_input",
)

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
                response = client.chat(
                    prompt, session_id=st.session_state.chat_session_id
                )

                # Handle different response formats
                if isinstance(response, str):
                    answer = response
                elif isinstance(response, dict):
                    answer = response.get(
                        "answer",
                        response.get("output", response.get("message", str(response))),
                    )
                else:
                    answer = str(response)

                message_placeholder.markdown(answer)
                # Store response with data if available
                msg_obj = {"role": "assistant", "content": answer}
                if isinstance(response, dict):
                    if "df" in response:
                        msg_obj["df"] = response["df"]
                    if "chart_type" in response:
                        msg_obj["chart_type"] = response["chart_type"]
                    if "graph_data" in response:
                        msg_obj["graph_data"] = response["graph_data"]
                
                st.session_state.messages.append(msg_obj)
                st.rerun()
            except Exception as e:
                st.error(f"Interaction Error: {str(e)}")
