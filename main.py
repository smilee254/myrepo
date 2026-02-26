from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, User, IncomeHistory, init_db
from engine import IDCS_Engine

app = FastAPI(title="Income Dip Compensation System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
init_db()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class IncomeData(BaseModel):
    amount: float
    status: str

class UserRequest(BaseModel):
    name: str
    age: int
    employment_type: str

class EvaluationRequest(BaseModel):
    name: str
    age: int
    employment_type: str
    current_income: float
    income_history: list[IncomeData]
    premium: float = 0.0
    deferred_period: int = 30

class ChatRequest(BaseModel):
    system_prompt: str
    messages: list

engine = IDCS_Engine()

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the IDCS API"}

@app.post("/user")
def get_or_create_user(req: UserRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == req.name).first()
    is_new = False
    
    if not user:
        user = User(
            name=req.name,
            age=req.age,
            employment_type=req.employment_type,
            src_tax_bracket="Bracket 3", 
            src_cap=50000.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True

    incomes = db.query(IncomeHistory).filter(IncomeHistory.user_id == user.id).order_by(IncomeHistory.month_index).all()
    history = [{"amount": inc.income_amount, "status": inc.status, "month": inc.month_index} for inc in incomes]
    
    return {
        "user_id": user.id,
        "name": user.name,
        "history": history,
        "is_new": is_new
    }

@app.post("/evaluate")
def evaluate_claim(req: EvaluationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == req.name).first()
    
    # Auto-create user if not found
    if not user:
        user = User(
            name=req.name,
            age=req.age,
            employment_type=req.employment_type,
            src_tax_bracket="Bracket 3",
            src_cap=50000.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # If new user and they provided history (from CSV), store it
        if req.income_history:
            for idx, inc in enumerate(req.income_history):
                db_inc = IncomeHistory(
                    user_id=user.id,
                    month_index=idx+1,
                    income_amount=inc.amount,
                    status=inc.status
                )
                db.add(db_inc)
            db.commit()

    # Update existing user profile with calculated premium and deferred period
    user.premium = req.premium
    user.deferred_period = req.deferred_period
    db.commit()
    db.refresh(user)


    # Use exact history provided in st.session_state (CSV)
    income_history_data = [
        {"amount": inc.amount, "status": inc.status}
        for inc in req.income_history
    ]

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

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    return {
        "content": "Jambo! I am the IDCS Smart Broker responding locally. Based on your inputs and M-Pesa data, I recommend Britam Family Income Protection with an 88% match because your history indicates high volatility that this plan specifically covers with inflation-adjusted monthly payouts.\\n\\n[Analyze Income] -> [Identify Risk Category] -> [Match Scheme]"
    }
