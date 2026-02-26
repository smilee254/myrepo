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
    premium = Column(Float, default=0.0)
    deferred_period = Column(Integer, default=30)
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

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
