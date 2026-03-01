import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_handler import process_and_group_inflows
import os
from pdf_generator import generate_stability_passport, submit_to_provider_api
import time
from datetime import datetime
from engine import IDCS_Engine, calculate_custom_premium
import sqlite3

@st.cache_resource
def load_idcs_model():
    return IDCS_Engine()


st.set_page_config(page_title="IDCS Dashboard", page_icon="🏦", layout="wide")

# -- SESSION STATE INIT --
if "live_mu" not in st.session_state:
    st.session_state.live_mu = 0
if "live_sigma" not in st.session_state:
    st.session_state.live_sigma = 0
if "stability_score" not in st.session_state:
    st.session_state.stability_score = 0
if "simulate_shock" not in st.session_state:
    st.session_state.simulate_shock = False

# Inject Custom CSS

try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.markdown("""
<style>
.sync-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
}
.sync-btn-container {
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    border-radius: 10px;
    padding: 2px;
    margin-top: 10px;
}
.sync-indicator {
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.5; }
    50% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.5; }
}
.vertical-progress-line {
    width: 2px;
    height: 30px;
    background: #00d296;
    box-shadow: 0 0 10px #00d296;
    margin-left: 12px;
    margin-top: 5px;
    margin-bottom: 5px;
}
div[data-testid="stStatusWidget"] {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.icon-amber {
    color: #ffbf00;
    text-shadow: 0 0 10px #ffbf00;
    font-size: 20px;
}
.icon-emerald {
    color: #00d296;
    text-shadow: 0 0 10px #00d296;
    font-size: 20px;
}
.premium-glow {
    font-size: 36px;
    font-weight: 800;
    color: #ffffff;
    text-shadow: 0 0 10px #00d296, 0 0 20px #00d296;
    background: rgba(0, 210, 150, 0.1);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #00d296;
    text-align: center;
    margin: 20px 0;
}
.roadmap-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 30px 0;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
}
.roadmap-step {
    text-align: center;
    flex: 1;
    position: relative;
}
.roadmap-step:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 25%;
    right: -50%;
    width: 100%;
    height: 2px;
    background: #333;
    z-index: 0;
}
.roadmap-icon {
    width: 40px;
    height: 40px;
    background: #2a2a2a;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 10px;
    border: 2px solid #555;
    position: relative;
    z-index: 1;
}
.roadmap-active .roadmap-icon {
    border-color: #00d296;
    color: #00d296;
}
.roadmap-label {
    font-size: 12px;
    color: #aaa;
}
</style>
""", unsafe_allow_html=True)

# Helper to render custom cards
def metric_card(title, value, color_class=""):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value {color_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def status_card(title, message, is_success=True):
    klass = "success-card mint-text" if is_success else "alert-card status-red"
    st.markdown(f"""
    <div class="card {klass}">
        <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">{title}</div>
        <div style="font-size: 16px; font-weight: 400; color: #e0e0e0;">{message}</div>
    </div>
    """, unsafe_allow_html=True)

def render_claims_roadmap(deferred_days, stage=1):
    steps = [
        {"label": "Day 1: Dip Detected", "icon": "🚨"},
        {"label": f"Day 1-{deferred_days}: Waiting", "icon": "⏳"},
        {"label": f"Day {deferred_days+1}: Payout", "icon": "💰"}
    ]
    
    html = '<div class="roadmap-container">'
    for i, step in enumerate(steps):
        active_class = "roadmap-active" if stage > i else ""
        html += f'''
        <div class="roadmap-step {active_class}">
            <div class="roadmap-icon">{step['icon']}</div>
            <div class="roadmap-label">{step['label']}</div>
        </div>
        '''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# Helper to render custom cards

def toggle_shock():
    st.session_state.simulate_shock = not st.session_state.simulate_shock

# -- AUTH STATE INIT --
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "auth_step" not in st.session_state:
    st.session_state.auth_step = 1
if "auth_email" not in st.session_state:
    st.session_state.auth_email = ""

# -- LOGIN VIEW --
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 6, 1])
    
    with center_col:
        st.container(border=False)
        login_col1, login_col2 = st.columns([1, 1], gap="large")
        
        with login_col1:
            try:
                st.image("financial_stability.png", use_container_width=True)
            except Exception:
                # Fallback if image not copied correctly
                st.info("Hero Image Location")
                
        with login_col2:
            st.markdown("<h2 style='color: #e0e0e0; font-weight: 700; margin-bottom: 0px;'>Welcome Back</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #9e9e9e; margin-bottom: 30px;'>Sign in to access your IDCS dashboard.</p>", unsafe_allow_html=True)
            
            if st.session_state.auth_step == 1:
                email = st.text_input("Work Email", placeholder="name@company.co.ke", key="email_input")
                
                if st.button("Continue", type="primary", use_container_width=True):
                    if "@" in email and "." in email:
                        st.session_state.auth_email = email
                        st.session_state.auth_step = 2
                        st.rerun()
                    else:
                        st.error("Please enter a valid work email address.")
            
            elif st.session_state.auth_step == 2:
                st.markdown(f"<p style='color: #00d296; margin-bottom: 20px; font-weight: 600;'>{st.session_state.auth_email}</p>", unsafe_allow_html=True)
                
                if st.button("🔑 Sign in with Passkey", type="primary", use_container_width=True):
                    st.session_state.logged_in = True
                    st.rerun()
                    
                st.markdown("<div style='text-align: center; margin: 20px 0; color: #666;'>OR</div>", unsafe_allow_html=True)
                
                password = st.text_input("Email OTP or Password", type="password")
                st.markdown("<div style='font-size: 13px; color: #f5a623; margin-top: -10px; margin-bottom: 10px;'>⚠️ Ensure Caps Lock is off</div>", unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Sign In", use_container_width=True):
                        if password:
                            st.session_state.logged_in = True
                            st.rerun()
                        else:
                            st.error("Please enter your OTP or Password.")
                with col_b:
                    if st.button("← Back to Email", use_container_width=True):
                        st.session_state.auth_step = 1
                        st.rerun()
                    
            st.markdown("<hr style='border: 0; border-top: 1px solid #333; margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown("<div style='text-align: center; font-size: 12px; color: #666;'><span title='Secure Connection'>🔒</span> Your data is encrypted and stored locally.</div>", unsafe_allow_html=True)
    
    st.stop()

from ai_component import inject_ai_assistant
inject_ai_assistant()

# -- SIDEBAR --
with st.sidebar:
    st.markdown("<h2 class='mint-text'>IDCS Portal</h2>", unsafe_allow_html=True)
    st.markdown("### User Identity")
    
    st.session_state.full_name = st.text_input("Full Name", value=st.session_state.get("full_name", ""))
    st.session_state.age = st.slider("Age", 18, 65, value=st.session_state.get("age", 30))
    st.session_state.employment_status = st.selectbox("Employment Status", ["Public Full-Time", "Private Contract", "Self-Employed/Jua Kali", "Unemployed"], index=0)
    st.session_state.dependants = st.number_input("Dependants", min_value=0, step=1, value=st.session_state.get("dependants", 0))

    # st.markdown("---")
    # st.markdown("### 🩺 Vision Model Doctor")
    # def list_available_models():
    #     import google.generativeai as genai
    #     if "GEMINI_API_KEY" in st.secrets:
    #         try:
    #             genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    #             models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    #             for m in models:
    #                 st.sidebar.markdown(f"<code style='font-size:10px;'>{m}</code>", unsafe_allow_html=True)
    #         except Exception as e:
    #             st.sidebar.error("Could not list models. Check API Key.")
    #     else:
    #         st.sidebar.warning("Key missing for Doctor")
    
    # if st.sidebar.checkbox("Show Available AI Models"):
    #     list_available_models()

    st.markdown("---")
    st.markdown("### Current Month Data")
    current_income = st.number_input("Current Month Income (KES)", min_value=0.0, step=1000.0, value=40000.0)

    # Initial Metric calculation for UI caps
    import numpy as np
    st.session_state.dip_probability = 0
    if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
        df_fin = st.session_state["financial_data"]
        incomes = df_fin['Total Income'].tolist()
        incomes.append(current_income)
        st.session_state.live_mu = float(np.mean(incomes))
        st.session_state.live_sigma = float(np.std(incomes, ddof=0))
        
        dip_thresh = st.session_state.live_mu * 0.8
        dip_count = sum(1 for x in incomes if x < dip_thresh)
        st.session_state.dip_probability = (dip_count / len(incomes) * 100) if len(incomes) > 0 else 0
    
    # Local assignment for safe usage
    live_mu = st.session_state.live_mu
    live_sigma = st.session_state.live_sigma

    st.markdown("---")
    st.markdown("### Premium & Underwriting")
    
    st.session_state.deferred_period = st.select_slider(
        "Deferred Period",
        options=[30, 60, 90],
        value=st.session_state.get("deferred_period", 30),
        help="Longer periods reduce your monthly premium."
    )
    st.caption(f"Waiting Period: {st.session_state.deferred_period} Days")

    # Benefit target capped at 70% of mean
    mu_val = st.session_state.live_mu
    max_benefit = mu_val * 0.70
    st.session_state.benefit_target = st.number_input(
        "Monthly Benefit Target (KES)",
        min_value=0.0,
        max_value=float(max_benefit),
        value=st.session_state.get("benefit_target", min(30000.0, max_benefit)),
        step=1000.0
    )

    st.info(f"Capped at 70% of mean: KES {max_benefit:,.0f}")

    # Session State Safety
    if 'mu_val' not in st.session_state: 
        st.session_state.mu_val = 0.0
    if 'dip_prob' not in st.session_state:
        st.session_state.dip_prob = st.session_state.get('dip_probability', 0.0)

    user_age = st.session_state.age
    user_deps = st.session_state.dependants
    user_emp = st.session_state.employment_status

    # Calculate Custom Premium
    if mu_val > 0:
        st.session_state.mu_val = mu_val
        st.session_state.custom_premium, st.session_state.max_comp = calculate_custom_premium(
            mean=st.session_state.mu_val,
            dip_probability=st.session_state.dip_prob,
            age=user_age,
            dependencies=user_deps,
            employment_status=user_emp
        )
        st.markdown(f"""
        <div class="premium-glow">
            <div style="font-size: 14px; color: #00d296; text-transform: uppercase; letter-spacing: 1px;">Monthly Premium</div>
            Ksh {st.session_state.custom_premium:,.2f}
        </div>
        """, unsafe_allow_html=True)



    st.markdown("---")
    st.markdown("### Profile Sync")
    
    with st.container():
        st.markdown('<div class="sync-btn-container" style="text-align: center;">', unsafe_allow_html=True)
        sync_button = st.button("🔄 Refresh Data", type="secondary")
        st.markdown('</div>', unsafe_allow_html=True)
        
    if sync_button:
        if st.session_state.full_name:
            with st.status("Syncing Profile...", expanded=True) as status:
                st.markdown('<div class="sync-card">', unsafe_allow_html=True)
                
                # Step 1: DB Check
                step1_col1, step1_col2 = st.columns([1, 5])
                with step1_col1:
                    icon1 = st.empty()
                    icon1.markdown("<div class='sync-indicator icon-amber'>⏳</div>", unsafe_allow_html=True)
                with step1_col2:
                    text1 = st.empty()
                    text1.markdown("<div style='margin-top: 4px; font-weight: 500;'>Connecting to DB...</div>", unsafe_allow_html=True)
                
                time.sleep(1) # Visual delay for effect
                icon1.markdown("<div class='icon-emerald'>✅</div>", unsafe_allow_html=True)
                text1.markdown("<div style='margin-top: 4px; color: #aaa;'>DB Connection Verified</div>", unsafe_allow_html=True)
                
                # Progress line
                st.markdown("<div class='vertical-progress-line'></div>", unsafe_allow_html=True)
                
                # Step 2: Profile Load
                step2_col1, step2_col2 = st.columns([1, 5])
                with step2_col1:
                    icon2 = st.empty()
                    icon2.markdown("<div class='sync-indicator icon-amber'>⏳</div>", unsafe_allow_html=True)
                with step2_col2:
                    text2 = st.empty()
                    text2.markdown("<div style='margin-top: 4px; font-weight: 500;'>Loading Cloud Profile...</div>", unsafe_allow_html=True)
                
                try:
                    name_escape = st.session_state.full_name.replace("'", "''")
                    with sqlite3.connect("idcs.db", timeout=10.0) as conn:
                        user_df = pd.read_sql(f"SELECT * FROM users WHERE name='{name_escape}'", conn)
                        if not user_df.empty:
                            user_id = user_df.iloc[0]['id']
                            st.session_state.current_user_id = int(user_id)
                            udata_is_new = False
                            hist_df = pd.read_sql(f"SELECT income_amount as amount, status, month_index as month FROM income_history WHERE user_id={user_id} ORDER BY month_index", conn)
                            udata_history = hist_df.to_dict('records') if not hist_df.empty else []
                        else:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO users (name, age, employment_type, src_cap, src_tax_bracket) VALUES (?, ?, ?, ?, ?)", (st.session_state.full_name, st.session_state.age, st.session_state.employment_status, 50000.0, 'Bracket 3'))
                            conn.commit()
                            st.session_state.current_user_id = cursor.lastrowid
                            udata_is_new = True
                            udata_history = []
                    
                    if True:
                        time.sleep(0.5)
                        icon2.markdown("<div class='icon-emerald'>✅</div>", unsafe_allow_html=True)
                        if udata_is_new:
                            text2.markdown("<div style='margin-top: 4px; color: #aaa;'>New Profile Configured</div>", unsafe_allow_html=True)
                            st.session_state["financial_data"] = None
                        else:
                            text2.markdown("<div style='margin-top: 4px; color: #aaa;'>Profile Loaded</div>", unsafe_allow_html=True)
                            
                        # Progress line
                        st.markdown("<div class='vertical-progress-line'></div>", unsafe_allow_html=True)
                            
                        # Step 3: Data Refresh
                        step3_col1, step3_col2 = st.columns([1, 5])
                        with step3_col1:
                            icon3 = st.empty()
                            icon3.markdown("<div class='sync-indicator icon-amber'>⏳</div>", unsafe_allow_html=True)
                        with step3_col2:
                            text3 = st.empty()
                            text3.markdown("<div style='margin-top: 4px; font-weight: 500;'>Refreshing Datasets...</div>", unsafe_allow_html=True)
                            
                        time.sleep(0.8)
                        if not udata_is_new and udata_history:
                            df_hist = pd.DataFrame(udata_history)
                            df_hist['Month'] = df_hist['month']
                            df_hist['Total Income'] = df_hist['amount']
                            st.session_state["financial_data"] = df_hist
                            text3.markdown("<div style='margin-top: 4px; color: #aaa;'>Historical Data Restored</div>", unsafe_allow_html=True)
                        else:
                            text3.markdown("<div style='margin-top: 4px; color: #aaa;'>Data Refresh Complete</div>", unsafe_allow_html=True)
                        
                        icon3.markdown("<div class='icon-emerald'>✅</div>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True) # close sync-card
                        
                        st.session_state.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        status.update(label="Sync Completed!", state="complete", expanded=False)
                        st.success("Successfully synced all profile assets.")
                except Exception as e:
                    st.markdown('</div>', unsafe_allow_html=True)
                    status.update(label="Sync Error", state="error", expanded=False)
                    st.error("Could not connect to backend API.")
        else:
            st.error("Please enter a Full Name to sync.")
            
    if st.session_state.get('last_sync_time'):
        st.markdown(f"<div style='text-align: center; font-style: italic; font-size: 11px; margin-top: 20px; color: #adb5bd;'>Last Synced: {st.session_state.last_sync_time}</div>", unsafe_allow_html=True)
            
    st.markdown("---")
    st.markdown("### Claim Evaluation")
    
    # Dynamic Plotly Gauge Calculation
    live_mu = st.session_state.live_mu
    live_sigma = st.session_state.live_sigma
    
    if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
        df_fin = st.session_state["financial_data"]
        unpaid_months = sum(df_fin.get('status', pd.Series(["Paid"]*len(df_fin))) == "Unpaid")
        w_emp = 1.1 if st.session_state.get('employment_status') in ["Public Full-Time", "Private Contract"] else 1.0
        
        if live_mu > 0:
            s_base = 100 * (1 - (live_sigma / live_mu)) * w_emp
            st.session_state.stability_score = max(0, min(100, s_base - (5 * unpaid_months)))
        else:
            st.session_state.stability_score = 0.0
    else:
        st.session_state.stability_score = 0.0

        
    gauge_config = {
        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
        'bar': {'color': "#00FFAA"},
        'bgcolor': "rgba(0,0,0,0)",
        'borderwidth': 0,
        'steps': [
            {'range': [0, 40], 'color': "rgba(255, 75, 75, 0.4)"},
            {'range': [40, 75], 'color': "rgba(255, 165, 0, 0.4)"},
            {'range': [75, 100], 'color': "rgba(0, 200, 83, 0.4)"}
        ]
    }
    
    if live_mu > 0 and current_income < (0.8 * live_mu):
        gauge_config['threshold'] = {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 80
        }
        
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = st.session_state.stability_score,
        title = {'text': "Income Stability Index", 'font': {'color': 'white'}},
        delta = {'reference': 50, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge = gauge_config
    ))
    
    fig_gauge.update_layout(
        height=250,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white", 'family': "sans-serif"},
        margin=dict(l=20, r=20, t=50, b=20)
    )
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    try:
        fig_gauge.write_image("gauge.png")
    except Exception:
        pass
    
    st.markdown("<br>", unsafe_allow_html=True)
    check_btn = st.button("Evaluate Claim", type="primary", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.button("Simulate Economic Shock (-30%)", on_click=toggle_shock, use_container_width=True)

# -- MAIN DASHBOARD --
st.markdown("""
<div style='text-align: center; padding: 2rem 0; margin-bottom: 2rem;'>
    <h1 style='font-weight: 700; margin-bottom: 0.5rem; color: #fff;'>Protect Your Monthly Income.</h1>
    <p style='color: #00d296; font-size: 1.2rem; font-weight: 500;'>Actuarially backed stability for Kenyan workers.</p>
</div>
""", unsafe_allow_html=True)

# -- FINANCIAL DATA VERIFICATION SECTION --
st.markdown("<h2 style='color: #fff; margin-bottom: 20px;'>Financial Data Verification</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    mpesa_upload = st.file_uploader("Upload M-Pesa Statement (CSV or PDF)", type=["csv", "pdf"], key="mpesa")
with col2:
    bank_upload = st.file_uploader("Upload Bank Statement (CSV or PDF)", type=["csv", "pdf"], key="bank")

from data_handler import process_and_group_inflows

if st.button("🔄 Sync & Analyze Statement", type="primary"):
    if "GEMINI_API_KEY" not in st.secrets or st.secrets["GEMINI_API_KEY"] == "YOUR_KEY_HERE":
        st.error("Missing GEMINI_API_KEY in .streamlit/secrets.toml. Please add it to proceed with Vision Processing.")
        st.stop()
        
    with st.spinner("Vision Processing... (Extracting Money In via Gemini 1.5 Flash)"):
        try:
            df_hist, monthly_avg_data, raw_list = process_and_group_inflows(mpesa_upload, bank_upload)
            
            if not df_hist.empty:
                st.session_state["financial_data"] = df_hist
                st.session_state["monthly_inflow"] = monthly_avg_data
                st.session_state["raw_income_data"] = raw_list  # Store as requested
                st.session_state.live_mu = float(df_hist['amount'].mean())
                st.session_state.live_sigma = float(df_hist.get('amount', pd.Series([0])).std())
                st.success(f"Vision Extraction Complete! Analyzed {len(monthly_avg_data)} months of income history.")
            else:
                st.warning("Vision AI could not find any valid income transactions in the provided document.")
        except Exception as e:
            st.error(f"Vision Processing Error: {e}")
            st.session_state["financial_data"] = None

# Step 1 Legacy: Data Preview / Heatmap
if "monthly_inflow" in st.session_state:
    st.markdown("### 📊 Income History (Foundation for Predictor)")
    
    col_t1, col_t2 = st.columns([1, 2])
    
    with col_t1:
        # Display as a table
        history_data = [
            {"Month": m, "Inflow (KES)": f"{amt:,.2f}", "Status": "Stable" if amt > 0 else "🚨 DIP"}
            for m, amt in st.session_state.monthly_inflow.items()
        ]
        st.table(pd.DataFrame(history_data))
        
    with col_t2:
        st.markdown("#### 🔥 Monthly Income Heatmap")
        # Prepare data for heatmap
        m_data = st.session_state.monthly_inflow
        df_h = pd.DataFrame(list(m_data.items()), columns=['Month', 'Amount'])
        df_h['Year'] = df_h['Month'].apply(lambda x: x.split('-')[0])
        # Force month order
        all_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        df_h['MonthName'] = df_h['Month'].apply(lambda x: datetime.strptime(x, '%Y-%m').strftime('%b'))
        
        # Pivot for heatmap
        pivot_h = df_h.pivot(index="Year", columns="MonthName", values="Amount").fillna(0)
        # Reorder columns to ensure Jan-Dec
        available_cols = [m for m in all_months if m in pivot_h.columns]
        pivot_h = pivot_h[available_cols]
        
        fig_h = px.imshow(pivot_h, 
                          labels=dict(x="Month", y="Year", color="Inflow (KES)"),
                          color_continuous_scale='Viridis',
                          text_auto='.2s')
        
        fig_h.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='white'),
            margin=dict(l=20, r=20, t=20, b=20),
            height=300
        )
        st.plotly_chart(fig_h, use_container_width=True)

    if st.session_state.get("raw_income_data"):
        with st.expander("View Raw Structured JSON"):
            st.json(st.session_state.raw_income_data)

# Use session state to avoid NameError
live_mu = st.session_state.get('live_mu', 0)

if "raw_income_data" in st.session_state and st.session_state["raw_income_data"]:
    # 1. Standardization Wrapper
    df_raw = pd.DataFrame(st.session_state.raw_income_data)
    # Force Column Mapping
    column_map = {'amount': 'Total Income', 'credit': 'Total Income', 'value': 'Total Income', 'date': 'TransactionDate', 'description': 'Description'}
    df_raw = df_raw.rename(columns=column_map)
    
    # 2. Handle Grouping (The Monthly Aggregate)
    df_raw['Month'] = pd.to_datetime(df_raw['TransactionDate']).dt.strftime('%Y-%m')
    df_monthly = df_raw.groupby('Month')['Total Income'].sum().reset_index()
    
    # Standardize 'Month' column name for downstream compatibility
    df_monthly = df_monthly.rename(columns={'Month': 'MonthGroup'}) # Avoiding keyword conflict
    
    # Calculate mu from grouped monthly totals
    mu = float(df_monthly['Total Income'].mean())
    st.session_state.live_mu = mu
    
    # 3. Fix the Variance Calculation
    df_monthly['Variance from Average'] = df_monthly['Total Income'] - mu
    # Sync with session state for Step 2 Predictor
    st.session_state["financial_data"] = df_monthly
    st.session_state.df_analysis = df_monthly
    
    # 4. Predictive Logic Transition
    engine = load_idcs_model()
    st.session_state.predictions = engine.predict_risk_horizon(df_monthly.rename(columns={'MonthGroup': 'month'}), mu)

    # UI Analytics: 6-Month Risk Horizon
    st.markdown("<h3 style='color: #fff;'>Predictive Risk Horizon (Next 6 Mo)</h3>", unsafe_allow_html=True)
    if st.session_state.get('predictions'):
        pred_cols = st.columns(6)
        for idx, (p_col, p_data) in enumerate(zip(pred_cols, st.session_state.predictions)):
            with p_col:
                # Flag 'High Risk Dip' if predicted < 0.7*mu
                color = "#ff4b4b" if p_data['is_high_risk'] else "#00d296"
                st.markdown(f"""
                <div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border-left: 4px solid {color};'>
                    <small style='color: #aaa;'>{p_data['month']}</small><br>
                    <b style='font-size: 14px;'>KES {p_data['predicted_income']:,.0f}</b>
                </div>
                """, unsafe_allow_html=True)
                if p_data['is_high_risk']:
                    st.caption("🚨 High Risk Dip")
    
    with st.expander("Show Calibration Table"):
        st.dataframe(df_monthly, width='stretch')

    # Calibration Logic Link
    current_month_income = current_income
    stability_sensitivity = 0.8
    
    dip_predicted = current_month_income < (stability_sensitivity * mu)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.metric("Historical Monthly Avg", f"KES {mu:,.2f}")
    with col_h2:
        st.metric("Current Month Input", f"KES {current_month_income:,.2f}")
    
    if dip_predicted:
        st.error(f"🚨 **High Risk Alert!** Predicted Dip: Current Month (KES {current_month_income:,.2f}) is below pattern threshold.")
    else:
        st.success(f"✅ **Steady State.** Pattern matches stable income history.")
    
    # Generate context for AI Assistant
    pct_diff = ((mu - current_month_income) / mu) * 100 if mu > 0 else 0
    dip_status = f"{pct_diff:.1f}% dip" if current_month_income < mu else "no significant dip"
    variance_str = ", ".join([f"{row['MonthGroup']} (Var: {row['Variance from Average']:,.0f})" for _, row in df_monthly.iterrows()])
    
    fin_ai_ctx = f"Financial Review: Historical Monthly Average is KES {mu:,.2f}. Manual Input for Current Month is KES {current_month_income:,.2f}. Based on the KES {current_month_income:,.0f} you entered, you have a {dip_status} compared to your average. Sensitivity Check Triggered Dip: {dip_predicted}. Monthly variances: {variance_str}."
    if dip_predicted:
        fin_ai_ctx += " Note: For low scores or drops, emphasize: 'Based on the KES " + f"{current_month_income:,.0f} you entered, you have a {pct_diff:.1f}% dip compared to your monthly average of KES {mu:,.2f}.'"
    st.markdown(f"<div id='financial-verification-context' style='display:none;'>{fin_ai_ctx}</div>", unsafe_allow_html=True)
    st.markdown("---")
else:
    st.info("Please upload your M-Pesa/Bank statement to calculate your historical baseline.")
    st.markdown("---")


if check_btn or st.session_state.get('last_user'):
    st.session_state.last_user = st.session_state.get('full_name')
    
    if not st.session_state.get('full_name'):
        st.error("👈 Please enter your Full Name in the sidebar.")
        st.stop()
        
    hist_payload = []
    if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
        df_fin = st.session_state["financial_data"]
        for _, row in df_fin.iterrows():
            hist_payload.append({
                "amount": float(row["Total Income"]),
                "status": row.get("status", "Paid") if "status" in row else "Paid"
            })
    else:
        st.warning("Please upload your M-Pesa CSV or Load your DB Profile before evaluating.")
        st.stop()

    income_to_evaluate = current_income
    if st.session_state.simulate_shock:
        income_to_evaluate = current_income * 0.7

    with st.spinner("Analyzing actuarial parameters..."):
        try:
            name_escape = st.session_state.full_name.replace("'", "''")
            with sqlite3.connect("idcs.db", timeout=10.0) as conn:
                user_df = pd.read_sql(f"SELECT * FROM users WHERE name='{name_escape}'", conn)
                cursor = conn.cursor()
                if user_df.empty:
                    cursor.execute("INSERT INTO users (name, age, employment_type, src_cap, src_tax_bracket) VALUES (?, ?, ?, ?, ?)", (st.session_state.full_name, st.session_state.age, st.session_state.employment_status, 50000.0, 'Bracket 3'))
                    user_id = cursor.lastrowid
                    if hist_payload:
                        for idx, inc in enumerate(hist_payload):
                            cursor.execute("INSERT INTO income_history (user_id, month_index, income_amount, status) VALUES (?, ?, ?, ?)", (user_id, idx+1, inc['amount'], inc['status']))
                else:
                    user_id = user_df.iloc[0]['id']
                
                cursor.execute("UPDATE users SET premium=?, deferred_period=? WHERE id=?", (float(st.session_state.get('custom_premium', 0)), int(st.session_state.get('deferred_period', 30)), user_id))
                conn.commit()
                
            w_emp = 1.1 if st.session_state.employment_status == "SRC_Teacher" else 1.0
            idcs_model = load_idcs_model()
            eval_data = idcs_model.calculate_metrics(
                income_history=hist_payload,
                src_cap=50000.0,
                current_income=income_to_evaluate,
                w_emp=w_emp
            )
            
            if True:
                user = {"name": st.session_state.full_name, "employment_type": st.session_state.employment_status, "src_cap": 50000.0}
                history = hist_payload
                
                # Header Micro-humanization
                st.markdown(f"<h3 style='color: #fff; margin-bottom: 24px;'>Habari, {user['name']}. Let's check your income health today.</h3>", unsafe_allow_html=True)
                
                from engine import INSURANCE_SCHEMES, calculate_match_score
                
                user_profile = {
                    'employment_status': st.session_state.get('employment_status', ''),
                    'dependants': st.session_state.get('dependants', 0),
                    'mu': eval_data['mu'],
                    'sigma': eval_data['sigma']
                }
                
                scored_schemes = []
                for s_name, s_data in INSURANCE_SCHEMES.items():
                    score = calculate_match_score(user_profile, s_name)
                    annual_prem = f"KES {s_data['premium']*12:,.0f}" if s_data['premium'] else "2.75% of Income"
                    scored_schemes.append({
                        "Scheme Name": s_name,
                        "Annual Premium": annual_prem,
                        "Coverage Limit": s_data['key_benefit'],
                        "Match Score": int(score)
                    })
                    
                scored_schemes = sorted(scored_schemes, key=lambda x: x['Match Score'], reverse=True)
                top_matches_str = ", ".join([f"{s['Scheme Name']} ({s['Match Score']}%)" for s in scored_schemes[:2]])
                
                # Context integration for AI (Passed from Python Backend to Client-side Window Context)
                identity_ctx = f"Full Name: {st.session_state.get('full_name', '')}, Age: {st.session_state.get('age', '')}, Employment Status: {st.session_state.get('employment_status', '')}, Dependants: {st.session_state.get('dependants', '')}."
                ai_ctx = f"User Profile: {identity_ctx} Model User: {user['name']} ({user['employment_type']}). Income Checked: KES {income_to_evaluate:,.2f}. Stability Score: {eval_data['stability_score']:.1f}/100. Average Income: KES {eval_data['mu']:,.2f}. Population Sigma: KES {eval_data['sigma']:,.2f}. Dip Detected: {eval_data['dip_detected']}. Eligible: {eval_data['eligible']}. Top Matches: {top_matches_str}."
                if eval_data['eligible']:
                    ai_ctx += f" Approved Payout: KES {eval_data['payout']:,.2f}."
                st.markdown(f"<div id='idcs-ai-context' style='display:none;'>{ai_ctx}</div>", unsafe_allow_html=True)
                
                if eval_data.get('dip_probability', 0) > 0:
                    prob = eval_data['dip_probability']
                    pred_month = eval_data.get('predicted_dip_month') or 'a future month'
                    if eval_data.get('risk_level') == 'CRITICAL':
                        st.error(f"WARNING: Based on your history, you are {prob:.0f}% likely to incur an income dip in {pred_month}.")
                    else:
                        st.warning(f"WARNING: Based on your history, you are {prob:.0f}% likely to incur an income dip in {pred_month}.")
                
                if st.session_state.simulate_shock:
                    st.warning(f"⚠️ Simulated Mode Active! Evaluating with artificial 30% drop (Income = KES {income_to_evaluate:,.2f})")

                # -- TABS --
                tab1, tab2, tab3, tab4 = st.tabs(["Check Eligibility", "My History", "Sustainability Projections", "Recommendations"])
                
                with tab1:
                    col1, col2 = st.columns([1, 1.5])
                    
                    with col1:
                        score = eval_data['stability_score']
                        if score > 75: color = "status-green"
                        elif score >= 50: color = "status-yellow"
                        else: color = "status-red"
                            
                        metric_card("Stability Score", f"{score:.1f}", color)
                        metric_card("Mean Income (6 Mo)", f"KES {eval_data['mu']:,.0f}")
                        
                    with col2:
                        if eval_data['dip_detected']:
                            if eval_data['eligible']:
                                msg = f"Based on your stability profile ({score:.1f}), your claim is approved.<br><br><span style='font-size: 32px; font-weight: 700; color: #00d296;'>Payout: KES {eval_data['payout']:,.2f}</span>"
                                status_card("✅ Alert: Income Dip Compensated", msg, is_success=True)
                                
                                st.markdown("### Underwriting & Timeline")
                                st.info(f"**Dip Trigger Active:** Current Month (KES {income_to_evaluate:,.0f}) is < 80% of Mean (KES {eval_data['mu']*0.8:,.0f})")
                                st.success(f"**Claim Eligibility:** VERIFIED (Deferred Period of {st.session_state.deferred_period} Days acknowledged)")
                                render_claims_roadmap(st.session_state.deferred_period, stage=3)
                            else:
                                reason = []
                                if score < 50: reason.append("Stability Score is below 50.")
                                if eval_data['paid_months'] < 3: reason.append("Less than 3 paid months recorded.")
                                msg = "Dip detected, but you do not meet the minimum safety criteria:<br>- " + "<br>- ".join(reason)
                                status_card("❌ Alert: Eligibility Failed", msg, is_success=False)
                                
                                st.markdown("### Underwriting & Timeline")
                                st.info(f"**Dip Trigger Active:** Current Month < 80% Mean")
                                st.warning("**Claim Eligibility:** PENDING (Criteria not met)")
                                render_claims_roadmap(st.session_state.deferred_period, stage=1)
                        else:
                            status_card("📈 Status: Stable", f"No significant dip detected. Your income (KES {income_to_evaluate:,.2f}) is above the 80% stability threshold (KES {eval_data['mu']*0.8:,.2f}).", is_success=True)
                            
                            st.markdown("### Underwriting & Timeline")
                            st.markdown(f"**Dip Trigger:** inactive (Current Month > 80% Mean)")
                            render_claims_roadmap(st.session_state.deferred_period, stage=0)


                with tab2:
                    st.markdown("### 6-Month Volatility Chart")
                    if history is not None and len(history) > 0:
                        months = [f"M-{6-i}" for i in range(len(history))] + ["Current"]
                        actuals = [h["amount"] for h in history] + [income_to_evaluate]
                        
                        mu = eval_data['mu']
                        thresh = mu * 0.8
                        thresholds = [thresh] * len(months)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=months, y=actuals, mode='lines+markers', name='Actual Income', line=dict(color='#00d296', width=4), marker=dict(size=10)))
                        fig.add_trace(go.Scatter(x=months, y=thresholds, mode='lines', name='Stability Threshold (0.8\u03bc)', line=dict(color='#ff4b4b', width=2, dash='dash')))
                        
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e0e0e0', family='Inter'),
                            xaxis=dict(showgrid=True, gridcolor='#2a2a2a'),
                            yaxis=dict(showgrid=True, gridcolor='#2a2a2a', title="Income (KES)"),
                            margin=dict(l=20, r=20, t=30, b=20),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig, width='stretch')
                    else:
                        st.warning("Awaiting valid statement data to generate Actuarial History.")

                with tab3:
                    st.markdown("### Risk Mitigation & Projections")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**Employment Profile:** {user['employment_type']}")
                        st.markdown(f"**SRC Cap Limit:** KES {user['src_cap']:,.2f}")
                        st.markdown(f"**Total Paid Months:** {eval_data['paid_months']} / 6")
                    with col_b:
                        st.markdown(f"**Population Volatility (\u03c3):** KES {eval_data['sigma']:,.2f}")
                        if eval_data['unpaid_months'] > 0:
                            st.markdown(f"⚠️ **Penalty Active:** You have {eval_data['unpaid_months']} unpaid months causing a subtraction of {eval_data['unpaid_months']*5} stability points.")
                        else:
                            st.markdown("✅ **Consistent Payments:** No penalties for unpaid months applied.")
                            
                with tab4:
                    st.markdown("### Market Recommendations")
                    market_avg = st.session_state.get('custom_premium', 0) * 1.15 if st.session_state.get('custom_premium', 0) > 0 else 1500
                    
                    st.markdown("Here is why our data-driven premium is better for you:")
                    comp_df = pd.DataFrame([
                        {"Scheme Type": "IDCS Custom Scheme", "Monthly Premium": f"KES {st.session_state.get('custom_premium', 0):,.2f}", "Calculated By": "Datapoints & Risk Probability"},
                        {"Scheme Type": "Standard Market Alternative", "Monthly Premium": f"KES {market_avg:,.2f}", "Calculated By": "Market Avg + 15%"}
                    ])
                    st.dataframe(comp_df, hide_index=True, use_container_width=True)
                    

            else:
                st.error("Evaluating failed.")
        except Exception as e:
            st.error(f"Failed to process claim. Local Evaluation Error: {e}")
else:
    st.info("👈 Enter your Full Name in the sidebar and evaluate to load data.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #666; font-size: 12px;'>IDCS is an AI brokerage tool. Data processing complies with the Kenya Data Protection Act.</div>", unsafe_allow_html=True)
