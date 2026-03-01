import pandas as pd
import pdfplumber
import io
import json
import os
import streamlit as st
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
import google.generativeai as genai
from datetime import datetime

# --- 1. Pydantic Models for Validation ---

class IncomeData(BaseModel):
    """Schema for individual income transaction"""
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    amount: float = Field(..., description="Inflow amount (Float)")
    description: str = Field(..., description="Source or Details of inflow")

    @validator('date')
    def validate_date(cls, v):
        try:
            # Flexible parsing for AI convenience
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(v, fmt)
                    return dt.strftime("%Y-%m-%d")
                except:
                    continue
            return datetime.fromisoformat(v[:10]).strftime("%Y-%m-%d")
        except:
            raise ValueError(f"Invalid date format: {v}")

class AIInflowResult(BaseModel):
    """Root schema for AI response"""
    inflows: List[IncomeData]

# --- 2. Gemini Vision-Language Extractor ---

class IncomeVisionExtractor:
    def __init__(self):
        # Configure using st.secrets as requested
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            
            # Mission: Strictly extract IncomeData schema using structured output
            self.model = genai.GenerativeModel(
                model_name="models/gemini-2.5-flash",
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "inflows": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "date": {"type": "string"},
                                        "amount": {"type": "number"},
                                        "description": {"type": "string"}
                                    },
                                    "required": ["date", "amount", "description"]
                                }
                            }
                        },
                        "required": ["inflows"]
                    }
                }
            )
        except Exception:
            self.model = None

    def extract_inflows(self, file_content: bytes, is_mpesa: bool = True) -> List[Dict]:
        """
        Processes PDF and extracts ONLY inflows using Gemini 2.5 Flash.
        """
        if not self.model:
            raise ValueError("Gemini API Key missing in st.secrets['GEMINI_API_KEY']")

        # Extract text for context
        full_text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n--PAGE--\n"

        prompt = """
        Analyze this bank/M-Pesa statement. Identify and extract ONLY 'Money In' (Credit/Deposits). 
        Ignore all 'Debit', 'Withdrawal', or 'Sent' transactions.
        Return a JSON list with 'date', 'amount', and 'description'.
        
        DOCUMENT CONTENT:
        """ + full_text

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            # Extract JSON block
            if "```json" in raw_text:
                raw_json = raw_text.split("```json")[1].split("```")[0].strip()
            else:
                raw_json = raw_text.strip()
            
            data = json.loads(raw_json)
            # Validate with Pydantic
            validated = AIInflowResult(**data)
            return [item.dict() for item in validated.inflows]
        except Exception as e:
            st.error(f"AI Vision Error: {e}")
            return []

# --- 3. Data Anchoring & Monthly Aggregation ---

def process_and_group_inflows(mpesa_file=None, bank_file=None):
    """
    Main entry point for Dashboard.
    Groups 'amount' by month (YYYY-MM) and identifies missing months/Zero Income.
    Returns (DataFrame, monthly_inflow_dict, raw_list)
    """
    extractor = IncomeVisionExtractor()
    all_inflows = []

    if mpesa_file:
        all_inflows.extend(extractor.extract_inflows(mpesa_file.getvalue(), is_mpesa=True))
    if bank_file:
        all_inflows.extend(extractor.extract_inflows(bank_file.getvalue(), is_mpesa=False))

    if not all_inflows:
        return pd.DataFrame(), {}, []

    df = pd.DataFrame(all_inflows)
    df['Date'] = pd.to_datetime(df['date'])
    df['MonthYear'] = df['Date'].dt.strftime('%Y-%m')
    
    # Group by Month (YYYY-MM)
    monthly_inflow = df.groupby('MonthYear')['amount'].sum().to_dict()
    
    # Identify Missing Months (Simple range check)
    if monthly_inflow:
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        full_range = pd.date_range(start=min_date, end=max_date, freq='MS').strftime('%Y-%m').tolist()
        
        for m in full_range:
            if m not in monthly_inflow:
                monthly_inflow[m] = 0.0 # 100% Dip / Zero Income flagged
                
    # Sort for predictability
    sorted_monthly = dict(sorted(monthly_inflow.items()))
    
    return df, sorted_monthly, all_inflows
