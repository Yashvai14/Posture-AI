import logging
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.models import AuditLog

logger = logging.getLogger(__name__)


def record(
    db: Session,
    action: str,
    *,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | str | None = None,
    request: Request | None = None,
    **details,
) -> None:
    """Appends an audit entry in its own commit. Never raises: auditing must not break the user's request."""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=request.client.host if request and request.client else None,
                details=details,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("failed to write audit log", extra={"action": action})
