import io
import os
from fpdf import FPDF
import uuid

def generate_stability_passport(user_profile, match_data, out_path, gauge_img_path):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "Financial Stability Passport", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # User Info
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "User Profile", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Name: {user_profile.get('name', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Employment Status: {user_profile.get('employment_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Income Trend Summary
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "6-Month Income Trend Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Average Income (Mu): KES {user_profile.get('mu', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Volatility (Sigma): KES {user_profile.get('sigma', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Stability Score: {user_profile.get('stability_score', 0):.1f}/100", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Gauge Chart
    if os.path.exists(gauge_img_path):
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Stability Gauge", new_x="LMARGIN", new_y="NEXT")
        pdf.image(gauge_img_path, w=150)
        pdf.ln(5)
        
    # Match Details
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Recommended Scheme", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Scheme Name: {match_data.get('Scheme Name', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Match Score: {match_data.get('Match Score', 0)}% Match", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Key Benefit: {match_data.get('Coverage Limit', '')}", new_x="LMARGIN", new_y="NEXT")
    
    # Provide the PDF
    pdf.output(out_path)
    return out_path

# Mock API 
def submit_to_provider_api(user_data, pdf_path):
    # Simulate API interaction
    return str(uuid.uuid4())[:8].upper()
