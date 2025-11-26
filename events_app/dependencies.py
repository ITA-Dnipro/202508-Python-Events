from fastapi import Header, HTTPException, status, Request
from typing import Optional, List

class CurrentUser:
    def __init__(self, id: int, allowed_roles: List[str], role: Optional[str] = None):
        self.id = id
        self.allowed_roles = allowed_roles
        self.role = role 

async def get_current_user(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="user-id"),
    x_role: Optional[str] = Header(None, alias="role"),
    x_allowed_roles: Optional[str] = Header(None, alias="allowed-roles")
) -> CurrentUser:
    """
    Retrieves user data strictly from Trusted Headers injected by KrakenD.
    
    1. NO JWT decoding (prevents spoofing).
    2. NO logic merging roles (prevents privilege escalation).
    3. STRICT reliance on 'allowed-roles' header for permissions.
    """

    user_id_val = x_user_id or request.headers.get("user-id") or request.headers.get("User-ID")
    
    if not user_id_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not identified (Missing Trusted Headers)"
        )

    allowed_roles_val = x_allowed_roles or request.headers.get("allowed-roles") or request.headers.get("Allowed-Roles")
    
    final_allowed_roles = []
    if allowed_roles_val:
        final_allowed_roles = [r.strip() for r in allowed_roles_val.split(",") if r.strip()]

    final_role = x_role or request.headers.get("role") or request.headers.get("Role")

    print(f"DEBUG [Events Service] -> user_id: '{user_id_val}', role: '{final_role}', allowed_roles: {final_allowed_roles}", flush=True)
    try:
        return CurrentUser(
            id=int(user_id_val), 
            allowed_roles=final_allowed_roles, 
            role=final_role
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid User ID format in headers"
        )