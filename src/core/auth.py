import jwt
import datetime
import secrets
from typing import Optional
from settings import settings as config
from skills.logger import log_app

# Simple secret key for JWT (should be rotated or set in config)
JWT_SECRET = getattr(config, "JWT_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Expected condition for polled endpoints; log as audit but not as noisy app error
        log_audit("AUTH", "JWT signature expired")
        return None
    except Exception as e:
        log_app(f"Auth failed: {e}")
        return None

def generate_api_key() -> str:
    """Generate a sovereign API key for external integrations."""
    return f"tf_sk_{secrets.token_urlsafe(32)}"

def validate_api_key(key: str) -> bool:
    """
    Validate against stored keys in state.
    For now, we check the one in config if provided, or fallback to internal state.
    """
    if hasattr(config, "API_KEY") and key == config.API_KEY:
        return True
    
    # Check StateManager
    try:
        from core.state_manager import get_state_manager
        state = get_state_manager().get_state()
        keys = state.get("api_keys", [])
        return key in keys
    except Exception:
        return False
