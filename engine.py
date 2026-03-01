from prophet import Prophet
import numpy as np
import pandas as pd

class IDCS_Engine:
    def __init__(self):
        pass

    def predict_risk_horizon(self, df_monthly, mu):
        """
        Time-Series Forecasting using Prophet for the next 6 months.
        """
        if df_monthly.empty or mu <= 0:
            return [], 0, None
            
        # 1. Data Preparation for Prophet
        # Expects df_monthly to have 'month' (YYYY-MM) and 'Total Income'
        df_prophet = df_monthly.copy()
        df_prophet['ds'] = pd.to_datetime(df_prophet['month'])
        df_prophet = df_prophet.rename(columns={'Total Income': 'y'})
        
        # 2. Model Training
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(df_prophet[['ds', 'y']])
        
        # 3. 6-Month Horizon Forecast
        future = model.make_future_dataframe(periods=6, freq='MS')
        forecast = model.predict(future)
        
        # Extract predictions for the future 6 months
        predictions_df = forecast.tail(6).copy()
        
        # 4. Risk Scoring & Loading Factor
        # Dip Event: yhat_lower < (Average_Income * 0.7)
        threshold = mu * 0.7
        predictions_df['is_high_risk'] = predictions_df['yhat_lower'] < threshold
        
        risk_events = predictions_df['is_high_risk'].sum()
        # Risk Score (0-100) based on frequency and depth of predicted dips
        # Simple score: 1 risk event = 15 points, maxed at 100
        depth_penalty = 0
        if risk_events > 0:
            avg_dip_depth = (threshold - predictions_df[predictions_df['is_high_risk']]['yhat_lower']).mean()
            depth_penalty = min(50, (avg_dip_depth / threshold) * 100)
            
        risk_score = min(100, (risk_events * 10) + depth_penalty)
        
        predictions = []
        for _, row in predictions_df.iterrows():
            predictions.append({
                "month": row['ds'].strftime('%Y-%m'),
                "predicted_income": float(row['yhat']),
                "predicted_lower": float(row['yhat_lower']),
                "is_high_risk": bool(row['is_high_risk'])
            })
            
        return predictions, risk_score, (model, forecast)

    def calculate_metrics(self, income_history, src_cap, current_income, w_emp=1.0):
        """
        income_history: list of dicts with 'amount' and 'status'
        """
        amounts = [record['amount'] for record in income_history]
        statuses = [record['status'] for record in income_history]

        # 1. Mean Income (mu)
        mu = np.mean(amounts) if len(amounts) > 0 else 0

        # 2. Standard Deviation (sigma)
        sigma = np.std(amounts, ddof=0) if len(amounts) > 0 else 0

        # Pattern Analysis (The Dip Predictor)
        total_months = len(amounts)
        dip_threshold = 0.8 * mu
        dips = [i for i, amt in enumerate(amounts) if amt < dip_threshold]
        dip_count = len(dips)
        
        # Risk & Probability Assessment
        dip_probability = (dip_count / total_months * 100) if total_months > 0 else 0
        
        pattern_detected = False
        predicted_dip_month = None
        risk_level = "LOW"
        next_dip_idx = None
        
        if dip_count > 1:
            intervals = [dips[j] - dips[j-1] for j in range(1, dip_count)]
            if len(set(intervals)) == 1:
                pattern_interval = intervals[0]
                pattern_detected = True
                last_dip_idx = dips[-1]
                next_dip_idx = last_dip_idx + pattern_interval
                
                months_until_next = next_dip_idx - total_months
                import datetime
                import calendar
                current_month_num = datetime.datetime.now().month
                future_month_num = (current_month_num + months_until_next - 1) % 12 + 1
                future_month_name = calendar.month_name[future_month_num]
                
                predicted_dip_month = f"{future_month_name} (M-{pattern_interval})"
                
                if months_until_next <= 1:
                    risk_level = "CRITICAL"
                elif months_until_next <= 2:
                    risk_level = "HIGH"
                else:
                    risk_level = "MEDIUM"
        elif dip_probability >= 50:
            risk_level = "HIGH"
        elif dip_probability > 0:
            risk_level = "MEDIUM"

        current_dip_detected = bool(current_income < dip_threshold)

        # 3. Stability Score (S)
        unpaid_months = statuses.count("Unpaid")
        p_unpaid = 5 * unpaid_months
        
        if mu > 0:
            s_base = 100 * (1 - (sigma / mu)) * w_emp
            stability_score = max(0, s_base - p_unpaid)
        else:
            stability_score = 0

        # Eligibility
        paid_months = statuses.count("Paid")
        eligible = bool(current_dip_detected and paid_months >= 3 and stability_score >= 50)

        # Predicted Compensation (Capped at 70% of Mean income)
        predicted_compensation = 0.0
        if eligible:
            payout = min(src_cap, 0.70 * mu)
            predicted_compensation = max(0, payout)

        return {
            "mu": float(mu),
            "sigma": float(sigma),
            "stability_score": float(stability_score),
            "dip_detected": current_dip_detected,
            "eligible": eligible,
            "payout": float(predicted_compensation),
            "paid_months": paid_months,
            "unpaid_months": unpaid_months,
            "dip_probability": float(dip_probability),
            "risk_level": risk_level,
            "pattern_detected": pattern_detected,
            "predicted_dip_month": predicted_dip_month,
            "next_dip_idx": next_dip_idx
        }

def calculate_custom_premium(mean, dip_probability, age, dependencies, employment_status, risk_score=0):
    """
    Calculate IDCS custom premium based on deterministic Actuarial Formula.
    Premium = Base + (Dip_Probability_Loading * Risk_Score_Factor)
    """
    if mean <= 0:
        return 0.0, 0.0

    # Calculate 70% cap
    max_comp = mean * 0.7
    
    # Base premium logic (2% of mean)
    base = mean * 0.02
    
    # Risk loading logic (incorporating Prophet risk score)
    # risk_score is 0-100, normalize as a multiplier (1.0 to 2.5)
    r_multiplier = 1.0 + (risk_score / 100 * 1.5)
    
    # Historical dip probability adds a secondary load
    prob_load = (dip_probability / 100) * (mean * 0.01)
    
    premium = (base + prob_load) * r_multiplier
    
    return round(float(premium), 2), round(float(max_comp), 2)


INSURANCE_SCHEMES = {
    "Britam Family Income Protection": {
        "description": "Monthly payout for 3-10 years, 10% annual inflation adjustment. Premium ~3,000 KES/mo.",
        "premium": 3000,
        "key_benefit": "Monthly Cash Replacement"
    },
    "Liberty Combined Solution": {
        "description": "Temporary disability weekly wages + 96 months salary replacement. Best for formal employees.",
        "premium": 2000,
        "key_benefit": "Weekly Wages + Salary Replacement"
    },
    "Jubilee Bima Ya Mwananchi": {
        "description": "Micro-insurance for informal workers (Jua Kali). Low entry, daily hospital cash.",
        "premium": 500,
        "key_benefit": "Daily Hospital Cash"
    },
    "SHIF (Social Health Insurance Fund)": {
        "description": "2.75% of gross income. Mandatory baseline health cover.",
        "premium": None,
        "key_benefit": "Baseline Health Cover"
    }
}

def calculate_match_score(user_profile, scheme_name):
    score = 0
    scheme = INSURANCE_SCHEMES.get(scheme_name)
    if not scheme:
        return 0
        
    employment = str(user_profile.get('employment_status', '')).lower()
    is_formal = 'formal' in employment or 'public' in employment or 'private' in employment
    is_informal = 'informal' in employment or 'jua kali' in employment or 'self-employed' in employment
    
    dependants = int(user_profile.get('dependants', 0))
    mu = float(user_profile.get('mu', 0))
    sigma = float(user_profile.get('sigma', 0))
    
    # Base match scores logic
    volatility_high = (sigma > 0.15 * mu) if mu > 0 else False
    
    # Employment Match (+40)
    if 'liberty' in scheme_name.lower() and is_formal:
        score += 40
    elif 'jubilee' in scheme_name.lower() and is_informal:
        score += 40
        
    # Volatility Match (+30)
    desc_lower = scheme['description'].lower()
    if volatility_high and ('monthly' in desc_lower or 'weekly' in desc_lower):
        score += 30
        
    # Dependant Weight (+20)
    if dependants > 2 and 'family' in scheme_name.lower():
        score += 20
        
    # Affordability Deduction
    premium = scheme.get('premium')
    if premium is None: # for SHIF
        premium = mu * 0.0275 if mu else 0
        
    if mu > 0 and premium > (0.10 * mu):
        score -= 20
        
    return max(0, min(100, score))
