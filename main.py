from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, User, IncomeHistory, init_db
from engine import IDCS_Engine

app = FastAPI(title="Income Dip Compensation System API")

# Initialize DB on startup
init_db()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EvaluationRequest(BaseModel):
    user_id: int
    current_income: float

engine = IDCS_Engine()

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the IDCS API"}

@app.post("/evaluate")
def evaluate_claim(req: EvaluationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    incomes = db.query(IncomeHistory).filter(IncomeHistory.user_id == user.id).order_by(IncomeHistory.month_index).all()
    if len(incomes) != 6:
        raise HTTPException(status_code=400, detail="User does not have exactly 6 months of income history")

    income_history_data = [
        {"amount": inc.income_amount, "status": inc.status}
        for inc in incomes
    ]

    # Map employment_type to W_emp if desired. We'll use 1.0 for now, or 1.1 for SRC_Teacher to reward stability.
    w_emp = 1.1 if user.employment_type == "SRC_Teacher" else 1.0

    result = engine.calculate_metrics(
        income_history=income_history_data,
        src_cap=user.src_cap,
        current_income=req.current_income,
        w_emp=w_emp
    )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "employment_type": user.employment_type,
            "src_cap": user.src_cap
        },
        "evaluation": result,
        "income_history": income_history_data
    }
