import os, hashlib, hmac, secrets, time, json, base64
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

JWT_SECRET = os.getenv("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters. Set it in .env")

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_s, digest_s = stored.split("$")
        if scheme != "scrypt": return False
        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def create_token(user_id: int) -> str:
    now = int(time.time())
    header = b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
    payload = b64(json.dumps({"sub":str(user_id),"iat":now,"exp":now+60*60*24*7}, separators=(",",":")).encode())
    msg = f"{header}.{payload}".encode()
    sig = hmac.new(JWT_SECRET.encode(), msg, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64(sig)}"

def decode_token(token: str):
    try:
        h, p, s = token.split(".")
        msg = f"{h}.{p}".encode()
        expected = b64(hmac.new(JWT_SECRET.encode(), msg, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, s): return None
        payload = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        if payload.get("exp", 0) < time.time(): return None
        return int(payload["sub"])
    except Exception:
        return None

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "需要登录")
    uid = decode_token(authorization[7:])
    user = db.get(User, uid) if uid else None
    if not user: raise HTTPException(401, "登录已过期，请重新登录")
    return user
