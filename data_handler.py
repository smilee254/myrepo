import pandas as pd
import pdfplumber
import io

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
            # Read PDF directly from uploaded bytes
            with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_rows.extend(table)
            
            if len(all_rows) > 1:
                headers = [str(h).replace('\n', ' ').strip() for h in all_rows[0] if h is not None]
                data = all_rows[1:]
                raw_df = pd.DataFrame(data, columns=headers)
                
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
    except Exception as e:
        print(f"Parsing error: {e}")
        pass

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
            with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_rows.extend(table)
            
            if len(all_rows) > 1:
                headers = [str(h).replace('\n', ' ').strip() for h in all_rows[0] if h is not None]
                data = all_rows[1:]
                raw_df = pd.DataFrame(data, columns=headers)
                
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
    except Exception as e:
        print(f"Bank Parsing error: {e}")
        pass

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
    
    # Return mocked MVP data fallback if no sources provide valid data
    mock_df = pd.DataFrame({
        'Month': [1, 2, 3, 4, 5, 6],
        'Date': ['Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6'],
        'Total Income': [45000, 46000, 44000, 20000, 45000, 30000],
        'Description': ['Mock Salary']*6,
        'status': ['Paid', 'Paid', 'Paid', 'Paid', 'Paid', 'Paid']
    })
    return mock_df
