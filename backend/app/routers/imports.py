"""导入路由：JSON API 形式的 CSV 上传预览、确认导入与模板下载。"""
import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import MAX_UPLOAD_SIZE_BYTES
from app.database import get_db
from app.dependencies import require_user
from app.services.import_service import ImportError, ImportService

router = APIRouter(prefix="/api/imports", tags=["imports"])


class ConfirmImportRequest(BaseModel):
    """确认导入请求体。"""
    import_token: str


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """解析 CSV 并返回预览数据（不写入数据库）。"""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 .csv 文件")
    if file.size is not None and file.size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="文件大小不能超过 10MB")

    content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="文件大小不能超过 10MB")

    service = ImportService(db)
    try:
        preview = service.preview_import(user.id, content)
    except ImportError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    # 序列化 Decimal 为 float
    rows = []
    for row in preview["rows"]:
        r = dict(row)
        if r.get("amount") is not None:
            r["amount"] = float(r["amount"])
        rows.append(r)

    return {
        "token": preview["token"],
        "success_count": preview["success_count"],
        "duplicate_count": preview["duplicate_count"],
        "error_count": preview["error_count"],
        "rows": rows,
    }


@router.post("/confirm")
def confirm_import(
    payload: ConfirmImportRequest,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """确认导入：将预览通过的记录批量写入数据库。"""
    service = ImportService(db)
    try:
        result = service.confirm_import(user.id, payload.import_token)
    except ImportError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    return {
        "success": True,
        "message": f"导入完成，成功 {result['success_count']} 条",
        "result": result,
    }


@router.get("/template")
def download_template(user=Depends(require_user)):
    """下载 CSV 导入模板。"""
    del user
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "type", "amount", "category", "payment_method", "note"])
    writer.writerow(["2026-09-15", "expense", "50.00", "餐饮", "微信", "午餐"])
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template.csv"},
    )
