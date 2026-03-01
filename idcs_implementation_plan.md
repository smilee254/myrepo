# Income Dip Compensation System (IDCS) Implementation Plan

## Overview
This document outlines the structure, mathematical logic, and step-by-step execution to build the MVP for the Income Dip Compensation System (IDCS) tailored for the Kenyan labor market.

## Phase 1: Project & Environment Setup
1. **Initialize Directory**: Create a root project directory.
2. **Virtual Environment**: Create and activate a Python virtual environment (`python3 -m venv venv`).
3. **Dependencies**: Install and document requirements (`numpy`, `pandas`, `fastapi`, `uvicorn`, `streamlit`, `sqlalchemy`).

## Phase 2: Database Layer (`database.py`)
1. **ORM Setup**: Use SQLAlchemy to configure an SQLite database engine.
2. **Schema Definition**:
   - `User` Model: `id` (PK), `name`, `age`, `employment_type`, `src_tax_bracket`, `src_cap`.
   - `Income_History` Model: `id` (PK), `user_id` (FK to User), `month_index`, `income_amount`, `status` (String: "Paid" or "Unpaid").
3. **Data Seeding**: Create a script to populate the database with mock Kenyan users (e.g., an SRC Teacher and an IT worker in the Private Sector) along with their corresponding 6-month income histories.

## Phase 3: Actuarial Engine (`engine.py`)
Create the `IDCS_Engine` class with the following components:
1. **Input**: A user's `src_cap`, 6-month income history list, and their `current_income`.
2. **Metrics Calculation**:
   - `mu`: Mean of the 6-month income.
   - `sigma`: Population standard deviation of the 6-month income.
3. **Stability Score (S)**: 
   - Apply a defined weight (`W_emp`) based on employment type (e.g., fixed weight or dynamic parameter).
   - Penalize 5 points per unpaid month (`P_unpaid = 5 * unpaid_months`).
   - `S = max(0, [100 * (1 - (sigma / mu)) * W_emp] - P_unpaid)`.
4. **Dip Detection**: Returns True if `current_income < 0.8 * mu`.
5. **Eligibility**: Returns True if Dip Detected is True, the number of paid months >= 3, and `S >= 50`.
6. **Payout**: If eligible, calculate Payout as `min(SRC_Cap, 0.5 * (mu - current_income))`. Else, payout is 0. Returning these key fields in a structured format.

## Phase 4: Backend API (`main.py`)
1. **FastAPI Initialization**: Set up the FastAPI application instance.
2. **Endpoints**:
   - `POST /evaluate`: Accepts `user_id` and `current_income`.
   - **Logic**: Queries the SQLite database for the user's details and income history, processes the data through `IDCS_Engine`, and returns a detailed JSON payload containing score components, flags, and the final evaluated payout amount.

## Phase 5: Frontend Dashboard (`app.py`)
1. **Interface**: Create a Streamlit application providing a clean UI.
2. **Input Elements**: Input fields for `User ID` and `Current Income` alongside a check eligibility button.
3. **Integration**: When triggered, it will send an HTTP request to the FastAPI backend.
4. **Visuals**: Present the results (Mean Income, Stability Score, Dip Detected, Eligibility, and Payout Amount) intuitively to the user.
