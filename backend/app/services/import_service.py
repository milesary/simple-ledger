"""CSV 导入服务：解析、校验、重复检测与批量写入。"""
import csv
import hashlib
import io
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Transaction

# 内存中暂存待确认的导入数据，key 为 token
_pending_imports: dict[str, list[dict]] = {}

REQUIRED_HEADERS = {"date", "type", "amount", "category", "payment_method", "note"}


def compute_import_hash(
    date_str: str, type_: str, amount: Decimal, category: str,
    payment_method: str, note: str,
) -> str:
    """根据标准化后的字段计算导入哈希，用于重复检测。"""
    raw = "|".join([
        date_str,
        type_,
        f"{amount:.2f}",
        category,
        payment_method or "",
        note or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ImportError(Exception):
    """导入业务异常。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ImportService:
    """CSV 导入服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _load_category_map(self) -> dict[str, int]:
        """加载分类名称到 ID 的映射。"""
        rows = self.db.scalars(select(Category)).all()
        return {c.name: c.id for c in rows}

    def _normalize_type(self, value: str) -> str:
        """标准化收支类型。"""
        v = value.strip().lower()
        if v in ("income", "收入", "in"):
            return "income"
        if v in ("expense", "支出", "out"):
            return "expense"
        raise ImportError("type 必须是 income 或 expense")

    def _normalize_date(self, value: str) -> str:
        """标准化日期为 YYYY-MM-DD。"""
        v = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ImportError("日期格式不正确，需为 YYYY-MM-DD")

    def _normalize_amount(self, value: str) -> Decimal:
        """解析金额并校验大于 0。"""
        try:
            amount = Decimal(value.strip())
        except (InvalidOperation, ValueError) as exc:
            raise ImportError("金额必须是数字") from exc
        if amount <= 0:
            raise ImportError("金额必须大于 0")
        return amount.quantize(Decimal("0.01"))

    def preview_import(self, user_id: int, content: bytes) -> dict:
        """解析 CSV 并预览：返回统计与逐行状态，不写入数据库。"""
        category_map = self._load_category_map()

        # 解析 CSV（兼容 BOM）
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            raise ImportError("CSV 文件为空")
        missing = REQUIRED_HEADERS - set(h.strip() for h in reader.fieldnames)
        if missing:
            raise ImportError(f"缺少必要表头：{', '.join(sorted(missing))}")

        rows: list[dict] = []
        valid_rows: list[dict] = []
        seen_hashes: set[str] = set()
        success_count = 0
        duplicate_count = 0
        error_count = 0

        for line_no, row in enumerate(reader, start=2):
            try:
                date_str = self._normalize_date(row["date"])
                type_ = self._normalize_type(row["type"])
                amount = self._normalize_amount(row["amount"])
                category_name = row["category"].strip()
                if category_name not in category_map:
                    raise ImportError(f"分类「{category_name}」不存在")
                category_id = category_map[category_name]
                payment_method = (row.get("payment_method") or "").strip() or None
                note = (row.get("note") or "").strip() or None

                import_hash = compute_import_hash(
                    date_str, type_, amount, category_name, payment_method or "", note or "",
                )

                # 检测重复：文件内重复
                if import_hash in seen_hashes:
                    rows.append({
                        "line": line_no, "date": date_str, "type": type_,
                        "category": category_name, "amount": amount,
                        "note": note or "", "status": "duplicate",
                    })
                    duplicate_count += 1
                    continue
                seen_hashes.add(import_hash)

                # 检测重复：数据库中已存在
                exists = self.db.scalar(
                    select(Transaction).where(
                        Transaction.user_id == user_id,
                        Transaction.import_hash == import_hash,
                    )
                )
                if exists:
                    rows.append({
                        "line": line_no, "date": date_str, "type": type_,
                        "category": category_name, "amount": amount,
                        "note": note or "", "status": "duplicate",
                    })
                    duplicate_count += 1
                    continue

                rows.append({
                    "line": line_no, "date": date_str, "type": type_,
                    "category": category_name, "amount": amount,
                    "note": note or "", "status": "success",
                })
                valid_rows.append({
                    "user_id": user_id,
                    "type": type_,
                    "amount": amount,
                    "category_id": category_id,
                    "occurred_on": datetime.strptime(date_str, "%Y-%m-%d").date(),
                    "payment_method": payment_method,
                    "note": note,
                    "import_hash": import_hash,
                })
                success_count += 1

            except ImportError as exc:
                rows.append({
                    "line": line_no,
                    "date": (row.get("date") or "").strip(),
                    "type": (row.get("type") or "").strip(),
                    "category": (row.get("category") or "").strip(),
                    "amount": None,
                    "note": (row.get("note") or "").strip(),
                    "status": "error",
                    "error": str(exc),
                })
                error_count += 1

        token = secrets.token_hex(16)
        _pending_imports[token] = valid_rows

        return {
            "token": token,
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "rows": rows,
        }

    def confirm_import(self, user_id: int, token: str) -> dict:
        """根据 token 取出预览通过的行，在一个事务中批量写入。"""
        valid_rows = _pending_imports.pop(token, None)
        if valid_rows is None:
            raise ImportError("导入会话已过期，请重新上传")

        # 二次校验归属（token 对应的行必须属于当前用户）
        for row in valid_rows:
            if row["user_id"] != user_id:
                raise ImportError("导入数据与当前用户不匹配")

        inserted = 0
        for row in valid_rows:
            tx = Transaction(**row)
            self.db.add(tx)
            inserted += 1
        self.db.commit()

        return {
            "success_count": inserted,
            "duplicate_count": 0,
        }
