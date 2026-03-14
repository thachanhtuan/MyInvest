from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset
from app.schemas import AssetRead

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/", response_model=list[AssetRead])
def list_assets(db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.asset_class, Asset.name).all()
