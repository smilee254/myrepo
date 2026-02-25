import numpy as np
import pandas as pd

class IDCS_Engine:
    def __init__(self):
        pass

    def calculate_metrics(self, income_history, src_cap, current_income, w_emp=1.0):
        """
        income_history: list of dicts with 'amount' and 'status'
        """
        amounts = [record['amount'] for record in income_history]
        statuses = [record['status'] for record in income_history]

        # 1. Mean Income (mu)
        mu = np.mean(amounts) if len(amounts) > 0 else 0

        # 2. Standard Deviation (sigma) - population standard deviation
        sigma = np.std(amounts, ddof=0) if len(amounts) > 0 else 0

        # 3. Stability Score (S)
        unpaid_months = statuses.count("Unpaid")
        p_unpaid = 5 * unpaid_months
        
        if mu > 0:
            s_base = 100 * (1 - (sigma / mu)) * w_emp
            stability_score = max(0, s_base - p_unpaid)
        else:
            stability_score = 0

        # 4. Dip Detection
        dip_detected = bool(current_income < (0.8 * mu))

        # 5. Eligibility
        paid_months = statuses.count("Paid")
        eligible = bool(dip_detected and paid_months >= 3 and stability_score >= 50)

        # 6. Payout Amount
        if eligible:
            payout = min(src_cap, 0.5 * (mu - current_income))
            payout = max(0, payout) # ensure no negative payout
        else:
            payout = 0.0

        return {
            "mu": float(mu),
            "sigma": float(sigma),
            "stability_score": float(stability_score),
            "dip_detected": dip_detected,
            "eligible": eligible,
            "payout": float(payout),
            "paid_months": paid_months,
            "unpaid_months": unpaid_months
        }

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
