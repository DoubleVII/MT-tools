"""Tests for kiwix_reader config module."""

import os
import pytest
from unittest.mock import patch, mock_open

from kiwix_reader import config
from kiwix_reader.config import (
    Config,
    ZimFileConfig,
    load_config,
    get_config,
)


class TestConfigClasses:
    """Test configuration dataclasses."""

    def test_zim_file_config(self):
        """Test ZimFileConfig creation."""
        zf = ZimFileConfig(path="/path/to/file.zim", name="wikipedia", lang="en")
        assert zf.path == "/path/to/file.zim"
        assert zf.name == "wikipedia"
        assert zf.lang == "en"

    def test_config_get_zim_names(self):
        """Test Config.get_zim_names."""
        cfg = Config(
            zim_files=[
                ZimFileConfig(path="/a.zim", name="a", lang="en"),
                ZimFileConfig(path="/b.zim", name="b", lang="zh"),
            ]
        )
        assert cfg.get_zim_names() == ["a", "b"]

    def test_config_get_zim_langs(self):
        """Test Config.get_zim_langs."""
        cfg = Config(
            zim_files=[
                ZimFileConfig(path="/a.zim", name="a", lang="en"),
                ZimFileConfig(path="/b.zim", name="b", lang="zh"),
            ]
        )
        assert cfg.get_zim_langs() == ["en", "zh"]

    def test_config_get_zim_path(self):
        """Test Config.get_zim_path."""
        cfg = Config(
            zim_files=[
                ZimFileConfig(path="/a.zim", name="a", lang="en"),
                ZimFileConfig(path="/b.zim", name="b", lang="zh"),
            ]
        )
        assert cfg.get_zim_path("a") == "/a.zim"
        assert cfg.get_zim_path("b") == "/b.zim"
        assert cfg.get_zim_path("c") is None

    def test_config_get_zim_lang(self):
        """Test Config.get_zim_lang."""
        cfg = Config(
            zim_files=[
                ZimFileConfig(path="/a.zim", name="a", lang="en"),
                ZimFileConfig(path="/b.zim", name="b", lang="zh"),
            ]
        )
        assert cfg.get_zim_lang("a") == "en"
        assert cfg.get_zim_lang("b") == "zh"
        assert cfg.get_zim_lang("c") is None


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_empty(self):
        """Test load_config with no config file."""
        with patch("kiwix_reader.config.get_default_config_paths", return_value=[]):
            cfg = load_config()
            assert cfg.zim_files == []

    def test_load_config_from_yaml(self):
        """Test load_config from YAML content."""
        yaml_content = """
zim_files:
  - path: /path/to/wiki.zim
    name: wikipedia
    lang: en
  - path: /path/to/wiki_zh.zim
    name: wikipedia_zh
    lang: zh
"""
        with patch("kiwix_reader.config.get_default_config_paths", return_value=["/fake/config.yaml"]):
            with patch("builtins.open", mock_open(read_data=yaml_content)):
                cfg = load_config("/fake/config.yaml")
                assert len(cfg.zim_files) == 2
                assert cfg.zim_files[0].path == "/path/to/wiki.zim"
                assert cfg.zim_files[0].name == "wikipedia"
                assert cfg.zim_files[0].lang == "en"
                assert cfg.zim_files[1].lang == "zh"
