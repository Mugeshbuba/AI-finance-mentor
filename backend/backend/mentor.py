from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = "sqlite:///./finmentor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# Database Models
class User(Base):
    _tablename_ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    monthly_income = Column(Float)
    financial_goal = Column(String, default="")
    mood = Column(String, default="neutral")

class Transaction(Base):
    _tablename_ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    category = Column(String)
    date = Column(String)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class UserCreate(BaseModel):
    email: str
    name: str
    monthly_income: float
    financial_goal: Optional[str] = ""
    mood: Optional[str] = "neutral"

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    monthly_income: float
    financial_goal: str
    mood: str
    class Config:
        orm_mode = True

class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    category: str
    date: str

class TransactionOut(BaseModel):
    id: int
    user_id: int
    amount: float
    category: str
    date: str
    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints
@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/transactions/", response_model=TransactionOut)
def add_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == tx.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_tx = Transaction(**tx.dict())
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

@app.get("/users/{user_id}/transactions", response_model=List[TransactionOut])
def get_transactions(user_id: int, db: Session = Depends(get_db)):
    items = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    return items

@app.get("/users/{user_id}/summary")
def user_summary(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    total_spent = sum([t.amount for t in transactions])
    categories = {}
    for t in transactions:
        categories[t.category] = categories.get(t.category, 0) + t.amount
    return {
        "user": db_user.name,
        "financial_goal": db_user.financial_goal,
        "total_spent": total_spent,
        "category_breakdown": categories
    }

@app.post("/users/{user_id}/mood")
def update_mood(user_id: int, mood: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.mood = mood
    db.commit()
    return {"user_id": user_id, "mood": mood}

@app.get("/mentor_advice/{user_id}")
def mentor_advice(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    summary = f"{user.name} has spent {sum(t.amount for t in transactions):.2f} this month."
    response = "Keep up the good work! Consider investing extra funds if you're under budget."
    if user.mood == "stressed":
        response += " Take a deep breath before making new purchases."
    return {
        "summary": summary,
        "advice": response
    }
