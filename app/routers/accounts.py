from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=List[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()


@router.post("", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    if db.query(Account).filter(Account.id == payload.id).first():
        raise HTTPException(status_code=400, detail="Account id already exists")
    obj = Account(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{account_id}", response_model=AccountOut)
def update_account(account_id: str, payload: AccountUpdate, db: Session = Depends(get_db)):
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, db: Session = Depends(get_db)):
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(obj)
    db.commit()
