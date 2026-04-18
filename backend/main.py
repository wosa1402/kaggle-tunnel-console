from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import kaggle_service
from .auth import create_token, require_user, verify_credentials
from .config import FRONTEND_DIR
from .db import Account, get_db, init_db
from .schemas import AccountCreate, AccountOut, AccountUpdate, LoginRequest, TokenResponse

app = FastAPI(title="Kaggle Tunnel Console", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


# ---------- Auth ----------

@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_token(body.username))


@app.get("/api/auth/me")
def me(user: str = Depends(require_user)):
    return {"username": user}


# ---------- Accounts CRUD ----------

@app.get("/api/accounts", response_model=List[AccountOut])
def list_accounts(_: str = Depends(require_user), db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.id).all()


@app.post("/api/accounts", response_model=AccountOut)
def create_account(
    body: AccountCreate,
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    if db.query(Account).filter(Account.name == body.name).first():
        raise HTTPException(status_code=400, detail="Account name already exists")
    acc = Account(**body.model_dump())
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@app.patch("/api/accounts/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    body: AccountUpdate,
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(acc, k, v)
    db.commit()
    db.refresh(acc)
    return acc


@app.delete("/api/accounts/{account_id}")
def delete_account(
    account_id: int,
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(acc)
    db.commit()
    return {"ok": True}


# ---------- Kernel control ----------

@app.post("/api/accounts/{account_id}/start")
def start_kernel(
    account_id: int,
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        result = kaggle_service.push_kernel(acc)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["ok"]:
        acc.last_status = "queued"
        acc.last_run_at = datetime.utcnow()
        db.commit()
    else:
        acc.last_status = "error"
        db.commit()
    return result


@app.get("/api/accounts/{account_id}/status")
def get_status(
    account_id: int,
    _: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    result = kaggle_service.fetch_status(acc)
    if result["ok"]:
        acc.last_status = result["status"]
        db.commit()
    return {
        "id": acc.id,
        "name": acc.name,
        "status": acc.last_status,
        "last_run_at": acc.last_run_at,
        "tunnel_url": acc.tunnel_url,
        "raw": result.get("raw", ""),
    }


# ---------- Frontend ----------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
