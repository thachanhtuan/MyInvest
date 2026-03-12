from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, BondInfo
from app.schemas import AssetCreate, AssetOut, AssetUpdate, BondInfoCreate, BondInfoOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=List[AssetOut])
def list_assets(asset_class: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Asset)
    if asset_class:
        q = q.filter(Asset.asset_class == asset_class)
    return q.all()


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    if db.query(Asset).filter(Asset.ticker == payload.ticker).first():
        raise HTTPException(status_code=400, detail="Ticker already exists")
    obj = Asset(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{ticker}", response_model=AssetOut)
def update_asset(ticker: str, payload: AssetUpdate, db: Session = Depends(get_db)):
    obj = db.query(Asset).filter(Asset.ticker == ticker).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{ticker}", status_code=204)
def delete_asset(ticker: str, db: Session = Depends(get_db)):
    obj = db.query(Asset).filter(Asset.ticker == ticker).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(obj)
    db.commit()


# ─── Bond Info sub-resource ───────────────────────────────────────────────────

@router.get("/{ticker}/bond-info", response_model=BondInfoOut)
def get_bond_info(ticker: str, db: Session = Depends(get_db)):
    obj = db.query(BondInfo).filter(BondInfo.ticker == ticker).first()
    if not obj:
        raise HTTPException(status_code=404, detail="BondInfo not found")
    return obj


@router.post("/{ticker}/bond-info", response_model=BondInfoOut, status_code=201)
def upsert_bond_info(ticker: str, payload: BondInfoCreate, db: Session = Depends(get_db)):
    if not db.query(Asset).filter(Asset.ticker == ticker).first():
        raise HTTPException(status_code=404, detail="Asset not found")
    obj = db.query(BondInfo).filter(BondInfo.ticker == ticker).first()
    if obj:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
    else:
        data = payload.model_dump()
        data["ticker"] = ticker
        obj = BondInfo(**data)
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
