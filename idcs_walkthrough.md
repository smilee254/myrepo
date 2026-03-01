# IDCS System Walkthrough

This guide explains how to run the IDCS API backend and the Streamlit frontend.

## Prerequisites
1. Navigate to your project directory.
2. Ensure the virtual environment is activated:
   ```bash
   cd "/media/smilee/64 GB/new"
   source ~/idcs_venv/bin/activate
   ```

## 1. Start the FastAPI Backend
The backend runs on port `8000` and initializes the SQLite database upon startup automatically.

Run the following command in your terminal:
```bash
uvicorn main:app --reload
```

* You can view the automatically generated API documentation by navigating to `http://127.0.0.1:8000/docs` in your browser.

## 2. Start the Streamlit Frontend
Open a **new terminal window**, activate the virtual environment again, and run the Streamlit app.

```bash
cd "/media/smilee/64 GB/new"
source ~/idcs_venv/bin/activate
streamlit run app.py
```

* This will open the Streamlit dashboard in your web browser (usually at `http://localhost:8501`).

## 3. Testing the System
Once both servers are running:
1. Open the Streamlit dashboard.
2. Enter **User ID**: `1` (Amani Kenya, Teacher)
   - Try a current income of `40000` (No dip expected).
   - Try a current income of `20000` (Dip expected, should be eligible).
3. Enter **User ID**: `2` (Baraka Dev, IT Worker)
   - Try a current income of `90000` (No dip).
   - Try a current income of `50000` (Dip expected, should be eligible depending on stability score).

The system will accurately calculate their stability score and dip based on the mathematically specified actuarial logic.
