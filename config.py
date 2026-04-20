"""Configuration for UEFN MCP Server.

Centralizes all flags, constants, and defaults.
Can be overridden via environment variables.
"""

import os

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "0.3.0"

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

DEFAULT_PORT = int(os.environ.get("UEFN_MCP_PORT", "8765"))
MAX_PORT = 8770
HTTP_TIMEOUT_SEC = 30.0
# External MCP server request timeout (seconds). Kept as alias for clarity.
REQUEST_TIMEOUT = float(os.environ.get("UEFN_MCP_REQUEST_TIMEOUT", str(HTTP_TIMEOUT_SEC)))

# Heartbeat interval used by the external MCP server (seconds).
HEARTBEAT_INTERVAL = float(os.environ.get("UEFN_MCP_HEARTBEAT_INTERVAL", "10.0"))

# Max HTTP request size accepted by the UEFN listener (bytes).
# Protects the editor process from oversized payloads.
MAX_REQUEST_BYTES = int(os.environ.get("UEFN_MCP_MAX_REQUEST_BYTES", "2000000"))

# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

TICK_BATCH_LIMIT = 5
POLL_INTERVAL_SEC = 0.02
STALE_CLEANUP_SEC = 60.0
LOG_RING_SIZE = 200

# ---------------------------------------------------------------------------
# Security flags
# ---------------------------------------------------------------------------

# Auth token (optional). If set, requires X-MCP-Token header.
TOKEN = os.environ.get("UEFN_MCP_TOKEN", "")

# Read-only mode. Blocks all mutating commands when True.
READ_ONLY = os.environ.get("UEFN_MCP_READ_ONLY", "").lower() in ("1", "true", "yes")

# Enable execute_python (high risk). Disabled by default.
ENABLE_EXECUTE_PYTHON = os.environ.get(
    "UEFN_MCP_ENABLE_EXECUTE_PYTHON", ""
).lower() in ("1", "true", "yes")

# Debug mode. Enables verbose errors and tracebacks.
DEBUG = os.environ.get("UEFN_MCP_DEBUG", "").lower() in ("1", "true", "yes")

# Spawn policy: denylist of actor classes that should not be spawned.
# Comma-separated list. Defaults include known disallowed classes in UEFN.
SPAWN_ACTOR_CLASS_DENYLIST = {
    s.strip().lower()
    for s in os.environ.get("UEFN_MCP_SPAWN_ACTOR_CLASS_DENYLIST", "TextRenderActor").split(",")
    if s.strip()
}

# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

# Commands that only read state - always safe
READ_ONLY_COMMANDS = frozenset([
    "ping",
    "status",
    "get_log",
    "get_editor_log",
    "get_all_actors",
    "get_selected_actors",
    "get_actor_properties",
    "list_assets",
    "get_asset_info",
    "get_selected_assets",
    "does_asset_exist",
    "search_assets",
    "get_project_info",
    "get_level_info",
    "get_viewport_camera",
    # New tools
    "get_project_summary",
    "find_actors",
    "get_actor_details",
    "find_assets",
    # Verse tools
    "list_verse_files",
    "read_verse_file",
    "find_editable_bindings",
    "scan_verse_symbols",
])

# Commands that modify state - blocked in read-only mode
MUTATING_COMMANDS = frozenset([
    "spawn_actor",
    "set_actor_transform",
    "set_actor_properties",
    "select_actors",
    "focus_selected",
    "rename_asset",
    "duplicate_asset",
    "save_asset",
    "save_current_level",
    "set_viewport_camera",
])

# High-risk commands - require explicit enable flag
DANGEROUS_COMMANDS = frozenset([
    "execute_python",
    "delete_actors",
    "delete_asset",
    "shutdown",
])


def is_read_only_command(command: str) -> bool:
    """Check if command only reads state."""
    return command in READ_ONLY_COMMANDS


def is_mutating_command(command: str) -> bool:
    """Check if command modifies state."""
    return command in MUTATING_COMMANDS


def is_dangerous_command(command: str) -> bool:
    """Check if command is high-risk."""
    return command in DANGEROUS_COMMANDS


def is_command_allowed(command: str) -> tuple[bool, str]:
    """Check if command is allowed under current policy.
    
    Returns:
        (allowed: bool, reason: str if blocked, "" if allowed)
    """
    # Check dangerous commands first
    if is_dangerous_command(command):
        if command == "execute_python" and not ENABLE_EXECUTE_PYTHON:
            return False, "execute_python is disabled by policy. Set UEFN_MCP_ENABLE_EXECUTE_PYTHON=1 to enable."
        if command in ("delete_actors", "delete_asset") and READ_ONLY:
            return False, f"{command} is blocked in read-only mode."
        if command == "shutdown" and READ_ONLY:
            return False, "shutdown is blocked in read-only mode."
        return True, ""
    
    # Check mutating commands
    if is_mutating_command(command):
        if READ_ONLY:
            return False, f"{command} is blocked in read-only mode."
        return True, ""
    
    # Read-only commands always allowed
    if is_read_only_command(command):
        return True, ""
    
    # Unknown command - will be handled by dispatcher
    return True, ""


def check_auth(provided_token: str | None) -> tuple[bool, str]:
    """Check authentication.
    
    Returns:
        (authenticated: bool, error_message: str if failed)
    """
    if not TOKEN:
        # No token configured - auth disabled
        return True, ""
    
    if not provided_token:
        return False, "Authentication required. Provide X-MCP-Token header."
    
    if provided_token != TOKEN:
        return False, "Invalid authentication token."
    
    return True, ""
