"""
统一配置加载器。
优先级：环境变量 > config.yaml > 默认值
"""
import os
import sys
from pathlib import Path

import yaml

_PKG_ROOT = Path(__file__).resolve().parent.parent


def _expand_env(value):
    """递归展开字符串中的 ${ENV_VAR}。"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    if isinstance(value, str):
        import re
        for m in re.finditer(r'\$\{(\w+)\}', value):
            env_val = os.environ.get(m.group(1), "")
            value = value.replace(m.group(0), env_val)
        return value
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load(config_path=None):
    """加载配置。返回 dict，未配置必填字段返回 None 触发初始化。"""
    if config_path is None:
        config_path = _PKG_ROOT / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return None  # 首次使用，触发初始化

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg = _expand_env(cfg)

    # 展开 ~ 路径
    for section in ["paths"]:
        if section in cfg:
            for key, val in cfg[section].items():
                if isinstance(val, str) and "~" in val:
                    cfg[section][key] = str(Path(os.path.expanduser(val)).resolve())

    return cfg


def get_pkg_root():
    return _PKG_ROOT


def check_ffmpeg():
    """检查 ffmpeg 是否可用。"""
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True,
                       **{"creationflags": 0x08000000} if sys.platform == "win32" else {})
        return True
    except Exception:
        return False


def check_python():
    """返回 Python 版本字符串。"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
