from passlib.context import CryptContext
from jose import jwt

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password):
    return pwd_context.hash(password)


def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)


def create_token(email):
    return jwt.encode(
        {"sub": email},
        SECRET_KEY,
        algorithm=ALGORITHM
    )