# ============================================================
# core/rbac.py — Role-Based Access Control
#
# Owner is permanently registered. Other users can be added
# with restricted roles. Nobody else gets access.
# ============================================================

import os
import json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit

_RBAC_PATH = os.path.join(config.DATA_DIR, "rbac.json")

# Permission definitions per role
PERMISSIONS = {
    "owner": {"*"},  # Everything
    "admin": {
        "chat", "skills", "system", "todos", "backup", "think",
        "topics", "post", "evolve", "run",
    },
    "user": {
        "chat", "skills", "system", "todos", "topics", "think",
    },
    "viewer": {
        "chat", "skills",
    },
}


def _load() -> dict:
    from core.state_manager import state
    return state.get_section("rbac", {"owner_id": None, "users": {}})


def _save(data: dict):
    from core.state_manager import state
    state.update_section("rbac", data)


def register_owner(chat_id: int, name: str) -> bool:
    """Register the owner. Can only be done once."""
    data = _load()
    if data["owner_id"] is not None and data["owner_id"] != chat_id:
        log_audit("RBAC", f"Owner registration rejected — already set to {data['owner_id']}")
        return False

    data["owner_id"] = chat_id
    data["users"][str(chat_id)] = {
        "name": name,
        "role": "owner",
        "registered": datetime.now().isoformat(),
    }
    _save(data)
    config.TELEGRAM_ADMIN_CHAT_ID = chat_id
    log_audit("RBAC", f"Owner registered: {name} (ID: {chat_id})")
    return True


def add_user(chat_id: int, name: str, role: str = "user") -> bool:
    """Add a user with a specific role. Only owner can do this."""
    if role not in PERMISSIONS or role == "owner":
        return False

    data = _load()
    data["users"][str(chat_id)] = {
        "name": name,
        "role": role,
        "registered": datetime.now().isoformat(),
    }
    _save(data)
    log_audit("RBAC", f"User added: {name} (ID: {chat_id}) as {role}")
    return True


def remove_user(chat_id: int) -> bool:
    data = _load()
    key = str(chat_id)
    if key in data["users"] and data["users"][key]["role"] != "owner":
        del data["users"][key]
        _save(data)
        log_audit("RBAC", f"User removed: {chat_id}")
        return True
    return False


def get_role(chat_id: int) -> str:
    """Get user's role. Returns None if not registered."""
    data = _load()
    user = data["users"].get(str(chat_id))
    return user["role"] if user else None


def is_owner(chat_id: int) -> bool:
    return get_role(chat_id) == "owner"


def has_permission(chat_id: int, permission: str) -> bool:
    """Check if a user has permission for a specific command."""
    role = get_role(chat_id)
    if role is None:
        return False
    perms = PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def get_owner_id() -> int:
    data = _load()
    return data.get("owner_id")


def list_users() -> list[dict]:
    data = _load()
    return [
        {"id": int(uid), **info}
        for uid, info in data["users"].items()
    ]


def format_users() -> str:
    users = list_users()
    if not users:
        return "👤 No users registered."

    role_emoji = {"owner": "👑", "admin": "🛡️", "user": "👤", "viewer": "👁️"}
    lines = ["👥 *Registered Users*\n"]
    for u in users:
        em = role_emoji.get(u["role"], "👤")
        lines.append(f"  {em} {u['name']} — {u['role']} (ID: `{u['id']}`)")
    return "\n".join(lines)
