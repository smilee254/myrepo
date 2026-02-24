import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    employment_type = Column(String)
    src_tax_bracket = Column(String)
    src_cap = Column(Float)
    incomes = relationship("IncomeHistory", back_populates="user")

class IncomeHistory(Base):
    __tablename__ = 'income_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    month_index = Column(Integer)  # e.g., 1 to 6 (for the last 6 months)
    income_amount = Column(Float)
    status = Column(String)  # "Paid" or "Unpaid"
    user = relationship("User", back_populates="incomes")

DB_URL = "sqlite:///./idcs.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if empty
    if db.query(User).first() is None:
        # User 1: Teacher under SRC (Stable, no unpaid months)
        teacher = User(
            name="Amani Kenya",
            age=35,
            employment_type="SRC_Teacher",
            src_tax_bracket="Bracket 3",
            src_cap=50000.0
        )
        # User 2: Private Sector IT worker (Fluctuating, some unpaid)
        it_worker = User(
            name="Baraka Dev",
            age=28,
            employment_type="Private_IT",
            src_tax_bracket="Bracket 4",
            src_cap=80000.0
        )
        db.add_all([teacher, it_worker])
        db.commit()

        # Add 6 month income history
        # Teacher: Stable 40,000 per month, all paid
        teacher_incomes = [
            IncomeHistory(user_id=teacher.id, month_index=i, income_amount=40000.0, status="Paid")
            for i in range(1, 7)
        ]
        
        # IT Worker: Fluctuating, one unpaid
        it_incomes = [
            IncomeHistory(user_id=it_worker.id, month_index=1, income_amount=90000.0, status="Paid"),
            IncomeHistory(user_id=it_worker.id, month_index=2, income_amount=85000.0, status="Paid"),
            IncomeHistory(user_id=it_worker.id, month_index=3, income_amount=0.0, status="Unpaid"),
            IncomeHistory(user_id=it_worker.id, month_index=4, income_amount=95000.0, status="Paid"),
            IncomeHistory(user_id=it_worker.id, month_index=5, income_amount=88000.0, status="Paid"),
            IncomeHistory(user_id=it_worker.id, month_index=6, income_amount=92000.0, status="Paid"),
        ]
        
        db.add_all(teacher_incomes + it_incomes)
        db.commit()
    
    db.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded.")
