import os, secrets
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from .db import Base, engine, get_db
from .models import User, Endpoint, RequestLog
from .security import hash_password, verify_password, create_token, current_user

Base.metadata.create_all(bind=engine)
app = FastAPI(title="My Webhook API", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
class EndpointIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    response_code: int = Field(default=200, ge=100, le=599)
    response_body: str = Field(default='{"ok":true}', max_length=20000)
    active: bool = True

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "my-webhook"}

@app.post("/api/auth/register")
def register(data: AuthIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "这个邮箱已经注册")
    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"token": create_token(user.id), "email": user.email}

@app.post("/api/auth/login")
def login(data: AuthIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码不正确")
    return {"token": create_token(user.id), "email": user.email}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}

def owned_endpoint(endpoint_id: int, user: User, db: Session):
    ep = db.scalar(select(Endpoint).where(Endpoint.id == endpoint_id, Endpoint.owner_id == user.id))
    if not ep: raise HTTPException(404, "Endpoint 不存在")
    return ep

@app.get("/api/endpoints")
def list_endpoints(user: User = Depends(current_user), db: Session = Depends(get_db)):
    eps = db.scalars(select(Endpoint).where(Endpoint.owner_id == user.id).order_by(desc(Endpoint.id))).all()
    return [{"id":e.id,"name":e.name,"token":e.token,"active":e.active,"response_code":e.response_code,"response_body":e.response_body,"created_at":e.created_at.isoformat()} for e in eps]

@app.post("/api/endpoints")
def create_endpoint(data: EndpointIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ep = Endpoint(owner_id=user.id, name=data.name, token=secrets.token_urlsafe(24), active=data.active, response_code=data.response_code, response_body=data.response_body)
    db.add(ep); db.commit(); db.refresh(ep)
    return {"id":ep.id,"name":ep.name,"token":ep.token,"active":ep.active,"response_code":ep.response_code,"response_body":ep.response_body}

@app.patch("/api/endpoints/{endpoint_id}")
def update_endpoint(endpoint_id: int, data: EndpointIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ep = owned_endpoint(endpoint_id, user, db)
    ep.name=data.name; ep.active=data.active; ep.response_code=data.response_code; ep.response_body=data.response_body
    db.commit()
    return {"ok":True}

@app.delete("/api/endpoints/{endpoint_id}")
def delete_endpoint(endpoint_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ep = owned_endpoint(endpoint_id, user, db)
    db.delete(ep); db.commit()
    return {"ok":True}

@app.get("/api/logs")
def list_logs(limit: int = 100, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit=max(1,min(limit,300))
    rows=db.execute(select(RequestLog, Endpoint.name, Endpoint.token).join(Endpoint).where(Endpoint.owner_id==user.id).order_by(desc(RequestLog.id)).limit(limit)).all()
    return [{"id":l.id,"endpoint_id":l.endpoint_id,"endpoint_name":name,"token":token,"method":l.method,"path":l.path,"query_string":l.query_string,"headers":l.headers,"body":l.body,"client_ip":l.client_ip,"created_at":l.created_at.isoformat()} for l,name,token in rows]

@app.delete("/api/logs")
def clear_logs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=db.scalars(select(RequestLog).join(Endpoint).where(Endpoint.owner_id==user.id)).all()
    for row in rows: db.delete(row)
    db.commit()
    return {"ok":True,"deleted":len(rows)}

@app.api_route("/webhook/{token}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def receive_webhook(token: str, request: Request, db: Session = Depends(get_db)):
    ep=db.scalar(select(Endpoint).where(Endpoint.token==token, Endpoint.active==True))
    if not ep: return JSONResponse({"error":"Webhook not found or disabled"}, status_code=404)
    raw=await request.body()
    body=raw.decode("utf-8", errors="replace")
    headers={k:v for k,v in request.headers.items() if k.lower() not in {"authorization","cookie","set-cookie"}}
    log=RequestLog(endpoint_id=ep.id,method=request.method,path=str(request.url.path),query_string=str(request.url.query),headers=headers,body=body,client_ip=request.client.host if request.client else "")
    db.add(log); db.commit()
    return Response(content=ep.response_body, status_code=ep.response_code, media_type="application/json")

