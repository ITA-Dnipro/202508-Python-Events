from fastapi import Header, HTTPException, status, Request
from typing import Optional, List
import json
import base64

class CurrentUser:
    def __init__(self, id: int, allowed_roles: List[str], role: Optional[str] = None):
        self.id = id
        self.allowed_roles = allowed_roles
        self.role = role 

def decode_jwt_payload_safe(token: str):
    """
    Decodes JWT payload without signature verification.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        
        payload_b64 = parts[1]
        padding = '=' * (4 - len(payload_b64) % 4)
        payload_b64 += padding
        
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes)
    except Exception:
        return None

async def get_current_user(
    request: Request,
    user_id_header: Optional[str] = Header(None, alias="user_id"),
    authorization: Optional[str] = Header(None)
) -> CurrentUser:
    final_user_id = None
    final_role = None
    final_allowed_roles = []

    if user_id_header:
        final_user_id = user_id_header
        roles_str = request.headers.get("allowed_roles") or request.headers.get("Allowed-Roles")
        if roles_str:
            final_allowed_roles = roles_str.split(",")

    if not final_user_id and authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == 'bearer':
                payload = decode_jwt_payload_safe(token)
                if payload:
                    final_user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
                    final_role = payload.get("role")
                    
                    if final_role:
                        final_allowed_roles.append(final_role)
        except Exception:
            pass

    if not final_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not identified"
        )
    
    return CurrentUser(
        id=int(final_user_id), 
        allowed_roles=final_allowed_roles,
        role=final_role
    )