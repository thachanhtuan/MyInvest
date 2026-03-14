from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import DEFAULT_EXCEL_FILE
from app.database import get_db
from app.schemas import ImportResult
from app.services.export_service import export_balance_excel
from app.services.import_service import import_excel
from app.services.portfolio import get_portfolio_summary

router = APIRouter(prefix="/api", tags=["import-export"])


@router.post("/import/default", response_model=ImportResult)
def import_default_file(db: Session = Depends(get_db)):
    """Import from the default data.xlsx file."""
    if not DEFAULT_EXCEL_FILE.exists():
        return ImportResult(errors=[f"Файл не найден: {DEFAULT_EXCEL_FILE}"])
    return import_excel(db, DEFAULT_EXCEL_FILE)


@router.post("/import/excel", response_model=ImportResult)
def import_uploaded_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import from an uploaded Excel file."""
    if not file.filename or not file.filename.endswith(".xlsx"):
        return ImportResult(errors=["Файл должен иметь расширение .xlsx"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = import_excel(db, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return result


@router.get("/export/balance")
def export_balance(db: Session = Depends(get_db)):
    """Export current portfolio balance as Excel file."""
    summary = get_portfolio_summary(db)
    content = export_balance_excel(summary)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=balance.xlsx"},
    )
