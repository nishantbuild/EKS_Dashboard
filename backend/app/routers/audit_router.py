from fastapi import APIRouter, Depends, HTTPException, status

from app.audit import read_recent
from app.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def get_audit(limit: int = 200, user: CurrentUser = Depends(get_current_user)):
    if "admins" not in user.groups:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return read_recent(limit)
