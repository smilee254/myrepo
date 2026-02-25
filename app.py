import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="IDCS Dashboard", page_icon="🏦", layout="wide")

# Inject Custom CSS
try:
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

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
                st.image("financial_stability.png", use_container_width=True)
            except Exception:
                # Fallback if image not copied correctly
                st.markdown("<div style='height:300px;background:#2a2a2a;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#666;'>[Hero Image Location]</div>", unsafe_allow_html=True)
                
        with login_col2:
            st.markdown("<div style='padding: 2rem 0; padding-right: 2rem;'>", unsafe_allow_html=True)
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
                    st.session_state.authenticated = True
                    st.rerun()
                    
                st.markdown("<div style='text-align: center; margin: 20px 0; color: #666;'>OR</div>", unsafe_allow_html=True)
                
                password = st.text_input("Email OTP or Password", type="password")
                st.markdown("<div style='font-size: 13px; color: #f5a623; margin-top: -10px; margin-bottom: 10px;'>⚠️ Ensure Caps Lock is off</div>", unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Sign In", use_container_width=True):
                        if password:
                            st.session_state.authenticated = True
                            st.rerun()
                        else:
                            st.error("Please enter your OTP or Password.")
                with col_b:
                    if st.button("← Back to Email", use_container_width=True):
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
    st.markdown("User Profile & Input")
    
    user_id = st.number_input("Enter User ID", min_value=1, step=1, value=1)
    
    st.markdown("---")
    current_income = st.number_input("Current Month Income (KES)", min_value=0.0, step=1000.0, value=40000.0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    check_btn = st.button("Evaluate Claim")
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.button("Simulate Economic Shock (-30%)", on_click=toggle_shock)

# -- MAIN DASHBOARD --
st.markdown("""
<div style='text-align: center; padding: 2rem 0; margin-bottom: 2rem;'>
    <h1 style='font-weight: 700; margin-bottom: 0.5rem; color: #fff;'>Protect Your Monthly Income.</h1>
    <p style='color: #00d296; font-size: 1.2rem; font-weight: 500;'>Actuarially backed stability for Kenyan workers.</p>
</div>
""", unsafe_allow_html=True)

# -- FINANCIAL DATA VERIFICATION SECTION --
st.markdown("<h2 style='color: #fff; margin-bottom: 20px;'>Financial Data Verification</h2>", unsafe_allow_html=True)

from data_handler import process_financial_data

col1, col2 = st.columns(2)
with col1:
    mpesa_upload = st.file_uploader("Upload M-Pesa Statement (CSV)", type=["csv"], key="mpesa")
with col2:
    bank_upload = st.file_uploader("Upload Bank Statement (CSV)", type=["csv"], key="bank")

if st.button("Process Data", type="primary"):
    st.session_state["financial_data"] = process_financial_data(mpesa_upload, bank_upload)

if "financial_data" in st.session_state and st.session_state["financial_data"] is not None:
    df_fin = st.session_state["financial_data"]
    
    with st.expander("Advanced Calibration Settings", expanded=True):
        stability_sensitivity = st.slider("Stability Sensitivity", min_value=0.1, max_value=1.0, value=0.8, step=0.05)
    
    # Calculate Moving Average (mu) of the first 5 months
    first_5 = df_fin.head(5)
    mu = first_5['Total Income'].mean()
    
    # Set the 6th month as 'Current Month'
    current_month_income = df_fin.iloc[5]['Total Income'] if len(df_fin) >= 6 else df_fin.iloc[-1]['Total Income']
    
    # Variance from Average
    df_fin['Variance from Average'] = df_fin['Total Income'] - mu
    
    dip_predicted = current_month_income < (stability_sensitivity * mu)
    
    if dip_predicted:
        st.error(f"🚨 **Dip Predicted!** Current Month Income (KES {current_month_income:,.2f}) is below the {stability_sensitivity*100:.0f}% threshold of the 5-month moving average (KES {mu:,.2f}).")
    else:
        st.success(f"✅ **Stable Income!** Current Month Income (KES {current_month_income:,.2f}) is above the {stability_sensitivity*100:.0f}% threshold of the 5-month moving average (KES {mu:,.2f}).")
        
    st.markdown("### Calibration Summary")
    st.dataframe(df_fin[['Month', 'Total Income', 'Variance from Average']], use_container_width=True)
    
    # Generate context for AI Assistant
    variance_str = ", ".join([f"M{row['Month']} (Var: {row['Variance from Average']:,.0f})" for _, row in df_fin.iterrows()])
    fin_ai_ctx = f"Financial Review: 5-mo Average is KES {mu:,.2f}. Month 6 Income is KES {current_month_income:,.2f}. Sensitivity Check Triggered Dip: {dip_predicted}. Monthly variances from average computed from CSV data: {variance_str}."
    if dip_predicted:
        fin_ai_ctx += " Note: For low scores or drops, tell the user specific details e.g., 'Your income dropped in month 6 due to lower overall transactions/funds received compared to the 5-month average of KES " + f"{mu:,.2f}'."
    st.markdown(f"<div id='financial-verification-context' style='display:none;'>{fin_ai_ctx}</div>", unsafe_allow_html=True)
    st.markdown("---")

if check_btn or st.session_state.get('last_user'):
    st.session_state.last_user = user_id
    
    income_to_evaluate = current_income
    if st.session_state.simulate_shock:
        income_to_evaluate = current_income * 0.7

    with st.spinner("Analyzing actuarial parameters..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/evaluate",
                json={"user_id": user_id, "current_income": income_to_evaluate}
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data["user"]
                eval_data = data["evaluation"]
                history = data.get("income_history", [])
                
                # Header Micro-humanization
                st.markdown(f"<h3 style='color: #fff; margin-bottom: 24px;'>Habari, {user['name']}. Let's check your income health today.</h3>", unsafe_allow_html=True)
                
                # Context integration for AI (Passed from Python Backend to Client-side Window Context)
                ai_ctx = f"User: {user['name']} ({user['employment_type']}). Income Checked: KES {income_to_evaluate:,.2f}. Stability Score: {eval_data['stability_score']:.1f}/100. Average Income: KES {eval_data['mu']:,.2f}. Population Sigma: KES {eval_data['sigma']:,.2f}. Dip Detected: {eval_data['dip_detected']}. Paid Months: {eval_data['paid_months']}. Eligible: {eval_data['eligible']}."
                if eval_data['eligible']:
                    ai_ctx += f" Approved Payout: KES {eval_data['payout']:,.2f}."
                st.markdown(f"<div id='idcs-ai-context' style='display:none;'>{ai_ctx}</div>", unsafe_allow_html=True)
                
                if st.session_state.simulate_shock:
                    st.warning(f"⚠️ Simulated Mode Active! Evaluating with artificial 30% drop (Income = KES {income_to_evaluate:,.2f})")

                # -- TABS --
                tab1, tab2, tab3 = st.tabs(["Check Eligibility", "My History", "Sustainability Projections"])
                
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
                        st.plotly_chart(fig, use_container_width=True)
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
            else:
                st.error(f"Evaluating failed (Status {response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Failed to connect to the backend API. Please make sure the FastAPI server is running.")
else:
    st.info("👈 Enter a User ID in the sidebar and evaluate to load data.")
