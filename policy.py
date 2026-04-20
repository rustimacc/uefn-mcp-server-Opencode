"""Policy enforcement for UEFN MCP Server.

Separates security/permission logic from handlers.
"""

from config import (
    READ_ONLY,
    ENABLE_EXECUTE_PYTHON,
    DEBUG,
    TOKEN,
    is_dangerous_command,
    is_mutating_command,
    is_read_only_command,
)


# ---------------------------------------------------------------------------
# Command categories for documentation
# ---------------------------------------------------------------------------

COMMAND_CATEGORIES = {
    "system": {
        "description": "System status and control",
        "commands": ["ping", "status", "get_log", "shutdown", "execute_python"],
        "risk_level": "mixed",  # ping/status=safe, shutdown/execute=dangerous
    },
    "actors": {
        "description": "Actor manipulation",
        "commands": [
            "get_all_actors", "get_selected_actors", "get_actor_properties",
            "spawn_actor", "delete_actors", "set_actor_transform",
            "set_actor_properties", "select_actors", "focus_selected",
            "find_actors", "get_actor_details",
        ],
        "risk_level": "mixed",
    },
    "assets": {
        "description": "Asset management",
        "commands": [
            "list_assets", "get_asset_info", "get_selected_assets",
            "rename_asset", "delete_asset", "duplicate_asset",
            "does_asset_exist", "save_asset", "search_assets",
            "find_assets",
        ],
        "risk_level": "mixed",
    },
    "project": {
        "description": "Project information",
        "commands": ["get_project_info", "get_project_summary"],
        "risk_level": "read_only",
    },
    "level": {
        "description": "Level operations",
        "commands": ["save_current_level", "get_level_info"],
        "risk_level": "mixed",
    },
    "viewport": {
        "description": "Viewport control",
        "commands": ["get_viewport_camera", "set_viewport_camera"],
        "risk_level": "mixed",
    },
    "editor_log": {
        "description": "Editor output log",
        "commands": ["get_editor_log"],
        "risk_level": "read_only",
    },
    "verse": {
        "description": "Verse file context",
        "commands": [
            "list_verse_files", "read_verse_file",
            "find_editable_bindings", "scan_verse_symbols",
        ],
        "risk_level": "read_only",
    },
}


def get_command_category(command: str) -> str | None:
    """Get the category a command belongs to."""
    for category, info in COMMAND_CATEGORIES.items():
        if command in info["commands"]:
            return category
    return None


def get_command_risk_level(command: str) -> str:
    """Get risk level for a command.
    
    Returns: 'safe', 'mutating', or 'dangerous'
    """
    if is_dangerous_command(command):
        return "dangerous"
    if is_mutating_command(command):
        return "mutating"
    if is_read_only_command(command):
        return "safe"
    return "unknown"


def is_command_safe_in_read_only(command: str) -> bool:
    """Check if command can run in read-only mode."""
    return is_read_only_command(command) and not is_dangerous_command(command)


def validate_command(command: str, auth_token: str | None = None) -> tuple[bool, str, dict]:
    """Validate if a command can run.
    
    Returns:
        (allowed: bool, error_message: str, metadata: dict)
        
    metadata includes:
        - risk_level: str
        - category: str | None
        - auth_required: bool
        - auth_passed: bool
    """
    metadata = {
        "command": command,
        "risk_level": get_command_risk_level(command),
        "category": get_command_category(command),
        "read_only_mode": READ_ONLY,
        "execute_python_enabled": ENABLE_EXECUTE_PYTHON,
    }
    
    # Auth check
    if TOKEN:
        metadata["auth_required"] = True
        if not auth_token:
            return False, "Authentication required. Provide X-MCP-Token header.", metadata
        if auth_token != TOKEN:
            return False, "Invalid authentication token.", metadata
        metadata["auth_passed"] = True
    else:
        metadata["auth_required"] = False
        metadata["auth_passed"] = True
    
    # read-only mode check
    if READ_ONLY:
        if is_mutating_command(command):
            return False, f"Command '{command}' is blocked in read-only mode.", metadata
        if is_dangerous_command(command):
            return False, f"Command '{command}' is blocked in read-only mode.", metadata
    
    # Dangerous commands check
    if command == "execute_python":
        if not ENABLE_EXECUTE_PYTHON:
            return False, "execute_python is disabled by policy. Set UEFN_MCP_ENABLE_EXECUTE_PYTHON=1 to enable.", metadata
    
    return True, "", metadata


def get_policy_summary() -> dict:
    """Get current policy configuration summary."""
    return {
        "read_only_mode": READ_ONLY,
        "execute_python_enabled": ENABLE_EXECUTE_PYTHON,
        "auth_required": bool(TOKEN),
        "debug_mode": DEBUG,
        "command_categories": {
            cat: {
                "commands": info["commands"],
                "risk_level": info["risk_level"],
            }
            for cat, info in COMMAND_CATEGORIES.items()
        },
    }


def should_show_traceback() -> bool:
    """Check if full traceback should be shown in errors."""
    return DEBUG


def format_error(command: str, error: Exception, traceback_str: str | None = None) -> str:
    """Format an error message according to policy.
    
    In debug mode: show full traceback.
    In normal mode: show concise error message.
    """
    error_msg = str(error)
    
    if should_show_traceback() and traceback_str:
        return f"{error_msg}\n{traceback_str}"
    
    # Provide helpful context for common errors
    error_lower = error_msg.lower()
    
    if "not found" in error_lower:
        return error_msg
    
    if "actor not found" in error_lower:
        return error_msg
    
    if "asset not found" in error_lower:
        return error_msg
    
    if "timeout" in error_lower:
        return f"Command '{command}' timed out. The editor may be busy."
    
    # Generic fallback
    return error_msg