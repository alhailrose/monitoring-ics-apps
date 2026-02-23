"""
External configuration loader for AWS Monitoring Hub.
Loads config from ~/.monitoring-hub/config.yaml with fallback to built-in defaults.
"""

import os
from pathlib import Path
from typing import Any

import yaml

# Default config directory and file
CONFIG_DIR = Path.home() / ".monitoring-hub"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Built-in default profile groups (fallback if no external config)
DEFAULT_PROFILE_GROUPS = {
    "NABATI-KSNI": {
        "core-network-ksni": "207567759835",
        "data-ksni": "563983755611",
        "dc-trans-ksni": "982538789545",
        "edin-ksni": "288232812256",
        "eds-ksni": "701824263187",
        "epc-ksni": "783764594649",
        "erp-ksni": "992382445286",
        "etl-ksni": "654654389300",
        "hc-assessment-ksni": "909927813600",
        "hc-portal-ksni": "954030863852",
        "ksni-master": "317949653982",
        "ngs-ksni": "296062577084",
        "outdig-ksni": "465455994566",
        "outlet-ksni": "112555930839",
        "q-devpro": "528160043048",
        "sales-support-pma": "734881641265",
        "website-ksni": "637423330091",
    },
    "SADEWA": {
        "Diamond": "464587839665",
        "Techmeister": "763944546283",
        "KKI": "471112835466",
        "iris-dev": "522814711071",
        "bbi": "940404076348",
        "edot": "261622543538",
        "fresnel-phoenix": "197353582440",
        "fresnel-pialang": "510940807875",
        "fresnel-ykai": "339712722804",
    },
    "Aryanoble": {
        "HRIS": "493314732063",
        "fee-doctor": "084828597777",
        "cis-erha": "451916275465",
        "connect-prod": "620463044477",
        "public-web": "211125667194",
        "dermies-max": "637423567244",
        "tgw": "654654394944",
        "iris-prod": "522814722913",
        "sfa": "546158667544",
        "erha-buddy": "486250145105",
        "centralized-s3": "533267291161",
        "backup-hris": "390403877301",
        "dwh": "084056488725",
        "genero-empower": "941377160792",
    },
    "FFI": {
        "ffi": "315897480848",
    },
    "HungryHub": {"prod": "202255947274"},
    "Agung Sedayu": {"asg": "264887202956"},
    "Master": {
        "arbel-master": "477153214925",
        "ksni-master": "317949653982",
    },
    "NON SSO": {
        "nikp": "038361715485",
        "sandbox": "339712808680",
        "rumahmedia": "975050309328",
        "asg": "264887202956",
        "fresnel-master": "466650104955",
    },
}

# Built-in default settings
DEFAULT_SETTINGS = {
    "region": "ap-southeast-3",
    "workers": 5,
}

# Built-in display names for WhatsApp reports
DEFAULT_DISPLAY_NAMES = {
    "backup-hris": "Backup HRIS",
    "dwh": "DWH",
    "genero-empower": "Genero Empower",
    "ffi": "FFI",
    "HRIS": "HRIS",
    "cis-erha": "CIS Erha",
    "connect-prod": "Connect Prod",
    "tgw": "TGW",
    "centralized-s3": "Centralized S3",
    "erha-buddy": "ERHA BUDDY",
    "public-web": "Public Web App",
    "iris-prod": "PROD - IRIS PROD",
    "iris-dev": "DEV - IRIS DEV",
    "sfa": "SFA",
    "dermies-max": "Dermies Max",
    "fee-doctor": "Fee Doctor",
}


class Config:
    """Configuration manager with external file support."""

    def __init__(self):
        self._profile_groups: dict[str, dict[str, str]] = {}
        self._settings: dict[str, Any] = {}
        self._display_names: dict[str, str] = {}
        self._loaded = False

    def _load(self):
        """Load configuration from external file or use defaults."""
        if self._loaded:
            return

        # Start with defaults
        self._profile_groups = DEFAULT_PROFILE_GROUPS.copy()
        self._settings = DEFAULT_SETTINGS.copy()
        self._display_names = DEFAULT_DISPLAY_NAMES.copy()

        # Try to load external config
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    external_config = yaml.safe_load(f) or {}

                # Merge profile groups (external overrides/adds to defaults)
                profile_groups = external_config.get("profile_groups")
                if isinstance(profile_groups, dict):
                    for group_name, profiles in profile_groups.items():
                        if group_name in self._profile_groups:
                            if isinstance(profiles, dict):
                                self._profile_groups[group_name].update(profiles)
                        else:
                            if isinstance(profiles, dict):
                                self._profile_groups[group_name] = profiles

                # Merge settings
                defaults = external_config.get("defaults")
                if isinstance(defaults, dict):
                    self._settings.update(defaults)

                # Merge display names
                display_names = external_config.get("display_names")
                if isinstance(display_names, dict):
                    self._display_names.update(display_names)

            except yaml.YAMLError as e:
                print(f"Warning: Failed to parse config file: {e}")
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")

        self._loaded = True

    @property
    def profile_groups(self) -> dict[str, dict[str, str]]:
        """Get profile groups (lazy loaded)."""
        self._load()
        return self._profile_groups

    @property
    def settings(self) -> dict[str, Any]:
        """Get settings (lazy loaded)."""
        self._load()
        return self._settings

    @property
    def display_names(self) -> dict[str, str]:
        """Get display names (lazy loaded)."""
        self._load()
        return self._display_names

    @property
    def default_region(self) -> str:
        """Get default region."""
        return self.settings.get("region", "ap-southeast-3")

    @property
    def default_workers(self) -> int:
        """Get default number of parallel workers."""
        return self.settings.get("workers", 5)

    def config_exists(self) -> bool:
        """Check if external config file exists."""
        return CONFIG_FILE.exists()

    def get_config_path(self) -> Path:
        """Get the config file path."""
        return CONFIG_FILE


def create_sample_config() -> Path:
    """Create a sample configuration file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    sample_config = {
        "# AWS Monitoring Hub Configuration": None,
        "# This file is loaded from ~/.monitoring-hub/config.yaml": None,
        "": None,
        "defaults": {
            "region": "ap-southeast-3",
            "workers": 5,
        },
        "profile_groups": {
            "# Add your custom groups here": None,
            "my-group": {
                "profile-name": "123456789012",
                "another-profile": "234567890123",
            },
        },
        "display_names": {
            "# Friendly names for WhatsApp reports": None,
            "profile-name": "My Profile Display Name",
        },
    }

    # Write as YAML with comments preserved
    config_content = """# AWS Monitoring Hub Configuration
# This file is loaded from ~/.monitoring-hub/config.yaml
# 
# You can add/modify profile groups without changing the code.
# External config is merged with built-in defaults.

defaults:
  region: ap-southeast-3
  workers: 5

# Add your custom profile groups here
# These will be merged with built-in groups
profile_groups:
  # Example custom group:
  # my-company:
  #   prod-account: "123456789012"
  #   dev-account: "234567890123"

# Display names for WhatsApp backup reports
display_names:
  # Example:
  # my-profile: "My Friendly Name"
"""

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(config_content)

    return CONFIG_FILE


def get_sample_config_content() -> str:
    """Get sample config content for display."""
    return """# ~/.monitoring-hub/config.yaml

defaults:
  region: ap-southeast-3
  workers: 5

profile_groups:
  my-company:
    prod-account: "123456789012"
    dev-account: "234567890123"

display_names:
  prod-account: "Production"
  dev-account: "Development"
"""


# Global config instance (singleton)
_config = Config()


def get_config() -> Config:
    """Get the global config instance."""
    return _config


def get_profile_groups() -> dict:
    """Convenience function to get profile groups."""
    return _config.profile_groups


def get_display_names() -> dict:
    """Convenience function to get display names."""
    return _config.display_names


def get_default_region() -> str:
    """Convenience function to get default region."""
    return _config.default_region


def get_default_workers() -> int:
    """Convenience function to get default workers."""
    return _config.default_workers
