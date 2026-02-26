"""Configuration management for the virtual reality system."""

from virtual_reality.config.loader import load_config, save_config
from virtual_reality.config.schema import VirtualRealityConfig

__all__ = [
    "VirtualRealityConfig",
    "load_config",
    "save_config",
]
