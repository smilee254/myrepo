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
