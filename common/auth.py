from __future__ import annotations
import time
import jwt

SECRET_KEY = "hispalis-lab-shared-secret-DO-NOT-USE-IN-PRODUCTION"
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 8 * 3600

ROLES = ("employee", "dept_manager", "it_admin", "director")

USERS: dict[str, tuple[str, str, int]] = {
    "ana.garcia": ("employee", "rrhh", 1),
    "luis.perez": ("dept_manager", "rrhh", 2),
    "marta.ruiz": ("employee", "finanzas", 3),
    "carlos.soto": ("dept_manager", "finanzas", 4),
    "elena.vidal": ("it_admin", "it", 5),
    "javier.leon": ("employee", "it", 6),
    "sofia.reyes": ("director", "direccion", 7),
}

class InvalidSessionToken(Exception):
    pass

def issue_token(username: str) -> str:
    if username not in USERS:
        raise ValueError(f"Usuario desconocido: {username}")
    role, department, employee_id = USERS[username]
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "department": department,
        "employee_id": employee_id,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_and_decode_token(session_token: str) -> dict:
    if not session_token:
        raise InvalidSessionToken("Token de sesion ausente.")
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidSessionToken(f"Token de sesion invalido: {exc}") from exc
    if payload.get("role") not in ROLES:
        raise InvalidSessionToken("Rol de token no reconocido.")
    return payload

def require_role(session_token: str, *allowed_roles: str) -> dict:
    try:
        payload = verify_and_decode_token(session_token)
    except InvalidSessionToken as exc:
        raise PermissionError(str(exc)) from exc
    if payload["role"] not in allowed_roles:
        raise PermissionError(
            f"Rol '{payload['role']}' no autorizado para esta operacion "
            f"(roles permitidos: {', '.join(allowed_roles)})."
        )
    return payload
