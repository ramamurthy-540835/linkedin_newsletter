"""
Load, save, and validate platform YAML configs from backend/config/.
"""

import json
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
PLATFORMS_FILE = CONFIG_DIR / "platforms.json"
PLATFORM_CONFIGS_DIR = CONFIG_DIR / "platform-configs"


def _load_index() -> dict[str, Any]:
    if not PLATFORMS_FILE.exists():
        return {"platforms": {}}
    return json.loads(PLATFORMS_FILE.read_text(encoding="utf-8"))


def list_platforms() -> list[dict[str, Any]]:
    """Return all platforms sorted by priority, each with yaml_content."""
    index = _load_index()
    result = []
    for pid, info in index.get("platforms", {}).items():
        config_path = CONFIG_DIR / info["config_file"]
        yaml_content = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        result.append(
            {
                "id": pid,
                "name": _display_name(pid, yaml_content),
                "enabled": info.get("enabled", False),
                "priority": info.get("priority", 99),
                "yaml_content": yaml_content,
            }
        )
    return sorted(result, key=lambda x: x["priority"])


def load_platform_yaml(platform_id: str) -> str:
    """Return the raw YAML string for a platform."""
    index = _load_index()
    info = index.get("platforms", {}).get(platform_id)
    if not info:
        raise ValueError(f"Unknown platform: '{platform_id}'")
    config_path = CONFIG_DIR / info["config_file"]
    if not config_path.exists():
        raise FileNotFoundError(f"Config file missing: {config_path}")
    return config_path.read_text(encoding="utf-8")


def save_platform_yaml(platform_id: str, yaml_content: str) -> None:
    """Overwrite the YAML file for a platform."""
    index = _load_index()
    info = index.get("platforms", {}).get(platform_id)
    if not info:
        raise ValueError(f"Unknown platform: '{platform_id}'")
    config_path = CONFIG_DIR / info["config_file"]
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml_content, encoding="utf-8")


def set_platform_enabled(platform_id: str, enabled: bool) -> None:
    """Toggle enabled flag in platforms.json."""
    index = _load_index()
    if platform_id not in index.get("platforms", {}):
        raise ValueError(f"Unknown platform: '{platform_id}'")
    index["platforms"][platform_id]["enabled"] = enabled
    PLATFORMS_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def validate_yaml(yaml_content: str) -> tuple[bool, list[str]]:
    """Parse YAML and check required fields. Returns (is_valid, errors)."""
    errors: list[str] = []
    if not yaml_content.strip():
        return False, ["YAML content is empty"]
    try:
        parsed = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        return False, [f"YAML syntax error: {exc}"]

    if not isinstance(parsed, dict):
        return False, ["Root element must be a YAML mapping"]

    for field in ("name", "platform_id"):
        if field not in parsed:
            errors.append(f"Missing required field: '{field}'")

    if parsed.get("post_config"):
        cfg = parsed["post_config"]
        if not isinstance(cfg, dict):
            errors.append("'post_config' must be a mapping")
        elif "max_chars" in cfg and not isinstance(cfg["max_chars"], int):
            errors.append("'post_config.max_chars' must be an integer")

    return len(errors) == 0, errors


def _display_name(platform_id: str, yaml_content: str) -> str:
    try:
        parsed = yaml.safe_load(yaml_content) or {}
        return parsed.get("name", platform_id.capitalize())
    except Exception:
        return platform_id.capitalize()
