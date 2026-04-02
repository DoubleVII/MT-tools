"""Kiwix Reader configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class ZimFileConfig:
    """Configuration for a single ZIM file."""

    path: str
    name: str
    lang: str



@dataclass
class Config:
    """Main configuration class."""

    zim_files: List[ZimFileConfig] = field(default_factory=list)

    def get_zim_names(self) -> List[str]:
        """Get list of ZIM file names."""
        return [zf.name for zf in self.zim_files]

    def get_zim_path(self, name: str) -> Optional[str]:
        """Get ZIM file path by name."""
        for zf in self.zim_files:
            if zf.name == name:
                return zf.path
        return None

    def get_zim_lang(self, name: str) -> Optional[str]:
        """Get ZIM file language by name."""
        for zf in self.zim_files:
            if zf.name == name:
                return zf.lang
        return None
    

_config: Optional[Config] = None


def get_default_config_paths() -> List[str]:
    """Get default configuration file paths."""
    paths = []
    cwd_config = Path.cwd() / "kiwix_reader.yaml"
    if cwd_config.exists():
        paths.append(str(cwd_config))
    home_config = Path.home() / ".kiwix_reader" / "config.yaml"
    if home_config.exists():
        paths.append(str(home_config))
    return paths


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    global _config

    if config_path is None:
        paths = get_default_config_paths()
        if not paths:
            _config = Config()
            return _config
        config_path = paths[0]

    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}

    zim_files = []
    for zf in data.get("zim_files", []):
        zim_files.append(ZimFileConfig(path=zf["path"], name=zf["name"], lang=zf["lang"]))

    _config = Config(zim_files=zim_files)
    return _config


def get_config() -> Config:
    """Get current configuration."""
    global _config
    if _config is None:
        load_config()
    return _config


def get_zim_names() -> List[str]:
    """Get list of ZIM file names."""
    return get_config().get_zim_names()


def get_zim_path(name: str) -> Optional[str]:
    """Get ZIM file path by name."""
    return get_config().get_zim_path(name)
