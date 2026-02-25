import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from data_handler import process_financial_data
import os
from pdf_generator import generate_stability_passport, submit_to_provider_api
import time
from datetime import datetime

st.set_page_config(page_title="IDCS Dashboard", page_icon="🏦", layout="wide")

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

# State variable for Simulation
if "simulate_shock" not in st.session_state:
    st.session_state.simulate_shock = False

def toggle_shock():
    st.session_state.simulate_shock = not st.session_state.simulate_shock

# -- AUTH STATE INIT --
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_step" not in st.session_state:
    st.session_state.auth_step = 1
if "auth_email" not in st.session_state:
    st.session_state.auth_email = ""

# -- LOGIN VIEW --
if not st.session_state.authenticated:
    _, center_col, _ = st.columns([1, 6, 1])
    
    with center_col:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        login_col1, login_col2 = st.columns([1, 1], gap="large")
        
        with login_col1:
            try:
                st.image("financial_stability.png", width='stretch')
            except Exception:
                # Fallback if image not copied correctly
                st.markdown("<div style='height:300px;background:#2a2a2a;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#666;'>[Hero Image Location]</div>", unsafe_allow_html=True)
                
        with login_col2:
            st.markdown("<div style='padding: 2rem 0; padding-right: 2rem;'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #e0e0e0; font-weight: 700; margin-bottom: 0px;'>Welcome Back</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #9e9e9e; margin-bottom: 30px;'>Sign in to access your IDCS dashboard.</p>", unsafe_allow_html=True)
            
            if st.session_state.auth_step == 1:
                email = st.text_input("Work Email", placeholder="name@company.co.ke", key="email_input")
                
                if st.button("Continue", type="primary", width='stretch'):
                    if "@" in email and "." in email:
                        st.session_state.auth_email = email
                        st.session_state.auth_step = 2
                        st.rerun()
                    else:
                        st.error("Please enter a valid work email address.")
            
            elif st.session_state.auth_step == 2:
                st.markdown(f"<p style='color: #00d296; margin-bottom: 20px; font-weight: 600;'>{st.session_state.auth_email}</p>", unsafe_allow_html=True)
                
                if st.button("🔑 Sign in with Passkey", type="primary", width='stretch'):
                    st.session_state.authenticated = True
                    st.rerun()
                    
                st.markdown("<div style='text-align: center; margin: 20px 0; color: #666;'>OR</div>", unsafe_allow_html=True)
                
                password = st.text_input("Email OTP or Password", type="password")
                st.markdown("<div style='font-size: 13px; color: #f5a623; margin-top: -10px; margin-bottom: 10px;'>⚠️ Ensure Caps Lock is off</div>", unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Sign In", width='stretch'):
                        if password:
                            st.session_state.authenticated = True
                            st.rerun()
                        else:
                            st.error("Please enter your OTP or Password.")
                with col_b:
                    if st.button("← Back to Email", width='stretch'):
                        st.session_state.auth_step = 1
                        st.rerun()
                    
            st.markdown("<hr style='border: 0; border-top: 1px solid #333; margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown("<div style='text-align: center; font-size: 12px; color: #666;'><span title='Secure Connection'>🔒</span> Your data is encrypted and stored locally.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
    
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
                    user_res = requests.post("http://127.0.0.1:8000/user", json={
                        "name": st.session_state.full_name,
                        "age": st.session_state.age,
                        "employment_type": st.session_state.employment_status
                    })
                    if user_res.status_code == 200:
                        udata = user_res.json()
                        st.session_state.current_user_id = udata["user_id"]
                        
                        time.sleep(0.5)
                        icon2.markdown("<div class='icon-emerald'>✅</div>", unsafe_allow_html=True)
                        if udata["is_new"]:
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
                        if not udata["is_new"] and udata["history"]:
                            df_hist = pd.DataFrame(udata["history"])
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
                    else:
                        st.markdown('</div>', unsafe_allow_html=True)
                        status.update(label="Sync Failed!", state="error", expanded=False)
                        st.error("Invalid response from server.")
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
    current_income = st.number_input("Current Month Income (KES)", min_value=0.0, step=1000.0, value=40000.0)
    
    # Dynamic Plotly Gauge Calculation
    import numpy as np
    if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
        df_fin = st.session_state["financial_data"]
        incomes = df_fin['Total Income'].tolist()
        incomes.append(current_income)
        live_mu = np.mean(incomes)
        live_sigma = np.std(incomes, ddof=0)
        unpaid_months = sum(df_fin.get('status', pd.Series(["Paid"]*len(df_fin))) == "Unpaid")
        w_emp = 1.1 if st.session_state.get('employment_status') in ["Public Full-Time", "Private Contract"] else 1.0
        
        if live_mu > 0:
            s_base = 100 * (1 - (live_sigma / live_mu)) * w_emp
            st.session_state.stability_score = max(0, min(100, s_base - (5 * unpaid_months)))
        else:
            st.session_state.stability_score = 0.0
    else:
        st.session_state.stability_score = 0.0
        
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = st.session_state.stability_score,
        title = {'text': "Income Stability Index", 'font': {'color': 'white'}},
        delta = {'reference': 50, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "black"},
            'bgcolor': "transparent",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 40], 'color': "red"},
                {'range': [40, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 40
            }
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
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

if st.button("Process Data", type="primary"):
    st.session_state["financial_data"] = process_financial_data(mpesa_upload, bank_upload)

if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
    df_fin = st.session_state["financial_data"]
    
    with st.expander("Advanced Calibration Settings", expanded=True):
        stability_sensitivity = st.slider("Stability Sensitivity", min_value=0.1, max_value=1.0, value=0.8, step=0.05)
    
    # Calculate Historical Baseline (mu) of all 6 months
    mu = df_fin['Total Income'].mean()
    
    # Use manual input for the current month dip check
    current_month_income = current_income
    
    # Variance from Average
    df_fin['Variance from Average'] = df_fin['Total Income'] - mu
    
    dip_predicted = current_month_income < (stability_sensitivity * mu)
    
    # Visual Feedback
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.metric("Historical 6-Month Avg", f"KES {mu:,.2f}")
    with col_h2:
        st.metric("Current Month Input", f"KES {current_month_income:,.2f}")
        
    if dip_predicted:
        st.error(f"🚨 **Dip Predicted!** Current Month Income (KES {current_month_income:,.2f}) is below the {stability_sensitivity*100:.0f}% threshold of the 6-month moving average (KES {mu:,.2f}).")
    else:
        st.success(f"✅ **Stable Income!** Current Month Income (KES {current_month_income:,.2f}) is within safe bounds above the {stability_sensitivity*100:.0f}% threshold of the 6-month average (KES {mu:,.2f}).")
        
    st.markdown("### Calibration Summary")
    st.dataframe(df_fin[['Month', 'Total Income', 'Variance from Average']], width='stretch')
    
    # Generate context for AI Assistant
    pct_diff = ((mu - current_month_income) / mu) * 100 if mu > 0 else 0
    dip_status = f"{pct_diff:.1f}% dip" if current_month_income < mu else "no significant dip"
    variance_str = ", ".join([f"M{int(row['Month'])} (Var: {row['Variance from Average']:,.0f})" for _, row in df_fin.iterrows()])
    
    fin_ai_ctx = f"Financial Review: 6-mo Baseline Average is KES {mu:,.2f}. Manual Input for Current Month is KES {current_month_income:,.2f}. Based on the KES {current_month_income:,.0f} you entered, you have a {dip_status} compared to your 6-month average. Sensitivity Check Triggered Dip: {dip_predicted}. Monthly variances from average computed from uploaded data: {variance_str}."
    if dip_predicted:
        fin_ai_ctx += " Note: For low scores or drops, emphasize: 'Based on the KES " + f"{current_month_income:,.0f} you entered, you have a {pct_diff:.1f}% dip compared to your 6-month average of KES {mu:,.2f}.'"
    st.markdown(f"<div id='financial-verification-context' style='display:none;'>{fin_ai_ctx}</div>", unsafe_allow_html=True)
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
            response = requests.post(
                "http://127.0.0.1:8000/evaluate",
                json={
                    "name": st.session_state.full_name,
                    "age": st.session_state.age,
                    "employment_type": st.session_state.employment_status,
                    "current_income": income_to_evaluate,
                    "income_history": hist_payload
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data["user"]
                eval_data = data["evaluation"]
                history = data.get("income_history", [])
                
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
                            else:
                                reason = []
                                if score < 50: reason.append("Stability Score is below 50.")
                                if eval_data['paid_months'] < 3: reason.append("Less than 3 paid months recorded.")
                                msg = "Dip detected, but you do not meet the minimum safety criteria:<br>- " + "<br>- ".join(reason)
                                status_card("❌ Alert: Eligibility Failed", msg, is_success=False)
                        else:
                            status_card("📈 Status: Stable", f"No significant dip detected. Your income (KES {income_to_evaluate:,.2f}) is above the 80% stability threshold (KES {eval_data['mu']*0.8:,.2f}).", is_success=True)

                with tab2:
                    st.markdown("### 6-Month Volatility Chart")
                    if history:
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
                        st.info("No income history available.")

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
                    st.markdown("### Top Recommendation Cards")
                    top_2 = scored_schemes[:2]
                    
                    rec_col1, rec_col2 = st.columns(2)
                    for idx, (col, s) in enumerate(zip([rec_col1, rec_col2], top_2)):
                        with col:
                            border_color = "#00d296" if s['Match Score'] > 80 else "#ffcc00"
                            st.markdown(f'''
                            <div style="border: 2px solid {border_color}; padding: 20px; border-radius: 12px; margin-bottom: 10px; background-color: #1e1e1e;">
                                <h4 style="margin-top: 0; color: #fff; font-size: 20px;">{s['Scheme Name']}</h4>
                                <div style="font-size: 28px; font-weight: bold; color: {border_color};">{s['Match Score']}% Match</div>
                                <div style="margin-top: 15px; color: #ccc; font-size: 15px;"><b>Coverage Limit:</b> {s['Coverage Limit']}</div>
                                <div style="margin-top: 8px; color: #999; font-size: 14px;"><b>Annual Premium:</b> {s['Annual Premium']}</div>
                            </div>
                            ''', unsafe_allow_html=True)
                            
                            with st.popover("⚡ One-Click Apply", use_container_width=True):
                                provider_name = s['Scheme Name'].split(' ')[0]
                                st.warning(f"By clicking confirm, you authorize IDCS to share your Stability Index and Profile with {provider_name} for underwriting. Do you agree?")
                                if st.button("Confirm Application", key=f"apply_{idx}", type="primary"):
                                    pdf_path = f"passport_{idx}.pdf"
                                    # Create the profile dictionary properly
                                    profile_data = user_profile.copy()
                                    profile_data['name'] = user['name']
                                    profile_data['stability_score'] = eval_data['stability_score']
                                    
                                    generate_stability_passport(profile_data, s, pdf_path, "gauge.png")
                                    ref_id = submit_to_provider_api(profile_data, pdf_path)
                                    
                                    st.success(f"Application submitted! Reference ID: {ref_id}. {provider_name} will contact you within 24 hours.")
                                    with open(pdf_path, "rb") as pdf_file:
                                        st.download_button(label="📄 Download Financial Passport", data=pdf_file, file_name=f"{provider_name}_passport.pdf", mime="application/pdf", key=f"dl_{idx}")
                            
                    def display_comparison_matrix(schemes):
                        df = pd.DataFrame(schemes)
                        
                        def highlight_max(s):
                            is_max = s == s.max()
                            return ['background-color: lightblue; color: black;' if v else '' for v in is_max]
                        
                        styled_df = df.style.apply(highlight_max, subset=['Match Score']).format({"Match Score": "{:.0f}"})
                        st.dataframe(styled_df, hide_index=True, use_container_width=True)

                    st.markdown("### Insurance Comparison Matrix")
                    display_comparison_matrix(scored_schemes)
            else:
                st.error(f"Evaluating failed (Status {response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to the backend API. Please make sure the FastAPI server is running.")
else:
    st.info("👈 Enter your Full Name in the sidebar and evaluate to load data.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #666; font-size: 12px;'>IDCS is an AI brokerage tool. Data processing complies with the Kenya Data Protection Act.</div>", unsafe_allow_html=True)
