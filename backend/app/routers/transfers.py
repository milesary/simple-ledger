"""转账 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_user
from app.schemas import TransferCreate, TransferUpdate
from app.services.transfer_service import TransferError, TransferService

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("")
def list_transfers(
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """返回转账历史。"""
    return {"transfers": TransferService(db).list_transfers(user.id)}


@router.post("")
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """创建账户间转账。"""
    service = TransferService(db)
    try:
        transfer = service.create_transfer(user.id, payload)
    except TransferError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    result = next(
        item
        for item in service.list_transfers(user.id)
        if item["id"] == transfer.id
    )
    return {"success": True, "message": "转账已记录", "transfer": result}


@router.put("/{transfer_id}")
def update_transfer(
    transfer_id: int,
    payload: TransferUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """更新转账记录。"""
    service = TransferService(db)
    try:
        transfer = service.update_transfer(user.id, transfer_id, payload)
    except TransferError as exc:
        status = 404 if exc.message == "转账记录不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    result = next(
        item
        for item in service.list_transfers(user.id)
        if item["id"] == transfer.id
    )
    return {"success": True, "message": "转账已更新", "transfer": result}


@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """删除转账记录。"""
    try:
        TransferService(db).delete_transfer(user.id, transfer_id)
    except TransferError as exc:
        status = 404 if exc.message == "转账记录不存在" else 400
        raise HTTPException(status_code=status, detail=exc.message) from exc
    return {"success": True, "message": "转账已删除"}
