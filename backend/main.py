from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import User
from auth import (
    hash_password,
    verify_password,
    create_token
)

Base.metadata.create_all(bind=engine)

app = FastAPI()


class UserRequest(BaseModel):
    email: str
    password: str


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@app.post("/api/signup")
def signup(
    user: UserRequest,
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing:

        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    new_user = User(
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)

    db.commit()

    return {"message": "User created"}


@app.post("/api/login")
def login(
    user: UserRequest,
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not db_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        user.password,
        db_user.password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(db_user.email)

    return {"token": token}


@app.get("/api/dashboard")
def dashboard():

    return {
        "message": "Welcome to Databricks!"
    }