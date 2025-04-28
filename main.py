from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import os

# Setup FastAPI
app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./questions.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    answers = relationship("Answer", back_populates="user")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    answer_text = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))

    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Preload questions (safe auto-update)
def preload_questions(db: Session):
    # Delete all old questions first
    db.query(Question).delete()
    db.commit()

    # Now add fresh updated questions
    new_questions = [
        "What is your email address?",
        "What is your cell-phone number?",
        "What is your date of birth?",
        "What is your occupation?",
        "Who is your employer?",
        "How many years of investment experience do you have?",
        "What are your investment objectives? (e.g. Growth, Income, etc.)",
        "What is your Net Worth?",
        "Do you have any time limitation on your investment goals?",
        "Are you interested in life-insurance as well?"
    ]
    for q in new_questions:
        db.add(Question(text=q))
    db.commit()


# Routes
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/questions")
def get_questions(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(name=name).first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    questions = db.query(Question).all()
    return templates.TemplateResponse("questions.html", {"request": request, "user": user.name, "questions": questions})

@app.post("/submit")
async def submit_answers(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name")
    if not name:
        return RedirectResponse("/", status_code=302)

    user = db.query(User).filter_by(name=name).first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    for key, value in form.items():
        if key.startswith("question_"):
            qid = int(key.split("_")[1])
            answer = Answer(user_id=user.id, question_id=qid, answer_text=value)
            db.add(answer)
    db.commit()
    return templates.TemplateResponse("thankyou.html", {"request": request, "name": name})

@app.get("/results_login")
def results_login(request: Request):
    return templates.TemplateResponse("results_login.html", {"request": request})

@app.post("/results")
def view_results(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
    if code != "072823":
        return templates.TemplateResponse("results_login.html", {"request": request, "error": "Invalid code."})

    users = db.query(User).all()
    data = []
    for user in users:
        answers = [
            {"question": a.question.text, "answer": a.answer_text}
            for a in user.answers
        ]
        data.append({"name": user.name, "answers": answers})

    return templates.TemplateResponse("results.html", {"request": request, "results": data})

# Run preload once
with SessionLocal() as db:
    preload_questions(db)
