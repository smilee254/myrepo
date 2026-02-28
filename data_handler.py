import pandas as pd
import pdfplumber
import io
import re
import time

def universal_parser(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
        
    df = pd.DataFrame()
    filename = uploaded_file.name.lower()
    
    try:
        raw_df = pd.DataFrame()
        if filename.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
            
        elif filename.endswith('.pdf'):
            start_time = time.time()
            data = []
            with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                for page in pdf.pages:
                    if time.time() - start_time > 5:
                        return pd.DataFrame() # Stop timer: Abort early
                    text = page.extract_text()
                    if text:
                        for line in text.split('\n'):
                            date_m = re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', line)
                            amount_m = re.search(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', line)
                            if date_m and amount_m:
                                data.append({
                                    'Date': date_m.group(),
                                    'Details': line,
                                    'Paid In': amount_m.group().replace(',', '')
                                })
            raw_df = pd.DataFrame(data)
                
        if not raw_df.empty:
            # Match required M-Pesa Columns
            date_col, desc_col, amt_col = None, None, None
            for c in raw_df.columns:
                c_lower = str(c).lower()
                if 'completion time' in c_lower or 'receipt time' in c_lower or 'date' in c_lower:
                    if not date_col: date_col = c
                if 'details' in c_lower or 'description' in c_lower:
                    if not desc_col: desc_col = c
                # Only use 'Paid In' or 'Credit' column to ignore 'Paid Out' or 'Debit'
                if 'paid in' in c_lower or 'credit' in c_lower:
                    if not amt_col: amt_col = c
                    
            # Fallback if no specific direction is found (e.g. general Amount column)
            if not amt_col:
                for c in raw_df.columns:
                    if 'amount' in str(c).lower():
                        amt_col = c
                        break
                        
            if date_col and amt_col:
                raw_df = raw_df.dropna(subset=[amt_col, date_col])
                # Ensure Amount is numeric
                raw_df['Amount'] = raw_df[amt_col].astype(str).str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
                raw_df['Amount'] = pd.to_numeric(raw_df['Amount'], errors='coerce')
                
                # Drop any row where 'Paid In' is NaN or 0
                raw_df = raw_df.dropna(subset=['Amount'])
                raw_df = raw_df[raw_df['Amount'] > 0]
                
                # Keyword-based cleaning for Description
                if desc_col:
                    keywords = ['customer transfer', 'received', 'bank to m-pesa', 'merchant payment', 'commission']
                    
                    def is_valid_income(text):
                        t = str(text).lower()
                        # Ensure 'Transaction Fees' are NOT added back
                        if 'transaction fees' in t:
                            return False
                        return any(k in t for k in keywords)
                        
                    raw_df = raw_df[raw_df[desc_col].apply(is_valid_income)]
                    
                df['Date'] = raw_df[date_col]
                df['Description'] = raw_df[desc_col] if desc_col else 'Income'
                df['Total Income'] = raw_df['Amount']
            
            if df.empty:
                raise ValueError("No valid income data found in the file.")
                
    except Exception as e:
        raise ValueError(f"Invalid PDF format for M-Pesa: {e}")

    return df

def bank_parser(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
        
    df = pd.DataFrame()
    filename = uploaded_file.name.lower()
    
    try:
        raw_df = pd.DataFrame()
        if filename.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
            
        elif filename.endswith('.pdf'):
            start_time = time.time()
            data = []
            with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                for page in pdf.pages:
                    if time.time() - start_time > 5:
                        return pd.DataFrame() # Stop timer: Abort early
                    text = page.extract_text()
                    if text:
                        for line in text.split('\n'):
                            date_m = re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', line)
                            amount_m = re.search(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', line)
                            if date_m and amount_m:
                                data.append({
                                    'Date': date_m.group(),
                                    'Details': line,
                                    'Credit': amount_m.group().replace(',', '')
                                })
            raw_df = pd.DataFrame(data)
                
        if not raw_df.empty:
            date_col, desc_col, amt_col = None, None, None
            for c in raw_df.columns:
                c_lower = str(c).lower()
                if 'date' in c_lower or 'time' in c_lower:
                    if not date_col: date_col = c
                if 'details' in c_lower or 'description' in c_lower or 'particulars' in c_lower:
                    if not desc_col: desc_col = c
                if 'credit' in c_lower or c_lower == 'cr' or 'deposits' in c_lower:
                    if not amt_col: amt_col = c
                    
            if not amt_col:
                for c in raw_df.columns:
                    if 'amount' in str(c).lower():
                        amt_col = c
                        break
                        
            if date_col and amt_col:
                raw_df = raw_df.dropna(subset=[amt_col, date_col])
                
                # Verify and clean the Bank Amount string
                raw_df['Amount'] = raw_df[amt_col].astype(str)\
                                        .str.replace('Ksh', '', case=False, regex=True)\
                                        .str.replace('CR', '', case=False, regex=True)\
                                        .str.replace(',', '', regex=False)\
                                        .str.replace(' ', '', regex=False)
                
                raw_df['Amount'] = pd.to_numeric(raw_df['Amount'], errors='coerce')
                
                raw_df = raw_df.dropna(subset=['Amount'])
                # Filter 'Credit' > 0
                raw_df = raw_df[raw_df['Amount'] > 0]
                
                if desc_col:
                    ignore_keywords = ['transfer from savings to current', 'sweep', 'internal transfer']
                    focus_keywords = ['salary', 'eft', 'rtgs', 'mobile deposit', 'dividend']
                    
                    def is_valid_bank_income(text):
                        t = str(text).lower()
                        # Ignore self-transfers
                        if any(k in t for k in ignore_keywords):
                            return False
                        # Focus on keywords
                        return any(k in t for k in focus_keywords)
                        
                    raw_df = raw_df[raw_df[desc_col].apply(is_valid_bank_income)]
                    
                df['Date'] = raw_df[date_col]
                df['Description'] = raw_df[desc_col] if desc_col else 'Income'
                df['Total Income'] = raw_df['Amount']
                
            if df.empty:
                raise ValueError("No valid income data found in the file.")
                
    except Exception as e:
        raise ValueError(f"Invalid PDF format for Bank: {e}")

    return df

def process_financial_data(mpesa_csv, bank_csv):
    """
    Reads M-Pesa and Bank data (CSV/PDF).
    Returns a unified DataFrame with 'Month' and 'Total Income' calculated ONLY from inward credits.
    """
    dfs = []
    
    if mpesa_csv is not None:
        df_mpesa = universal_parser(mpesa_csv)
        if not df_mpesa.empty:
            dfs.append(df_mpesa)
            
    if bank_csv is not None:
        df_bank = bank_parser(bank_csv)
        if not df_bank.empty:
            dfs.append(df_bank)
            
    if dfs:
        # Merge this bank logic with the M-Pesa 'Paid In' logic
        combined_df = pd.concat(dfs, ignore_index=True)
        if 'Month' not in combined_df.columns:
            combined_df['Month'] = range(1, len(combined_df) + 1)
        combined_df['Total Income'] = combined_df['Total Income'].fillna(0)
        return combined_df
    
    # If no files were provided, return empty
    if mpesa_csv is None and bank_csv is None:
        return pd.DataFrame()
        
    raise ValueError("Invalid PDF format or no valid income data found.")
