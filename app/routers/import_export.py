from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.excel_service import export_to_excel, import_from_excel

router = APIRouter(tags=["import_export"])


@router.post("/import/excel")
async def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx / .xls files are accepted")
    content = await file.read()
    try:
        log = import_from_excel(io.BytesIO(content), db)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "log": log}


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    buffer = export_to_excel(db)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=myinvest_export.xlsx"},
    )
