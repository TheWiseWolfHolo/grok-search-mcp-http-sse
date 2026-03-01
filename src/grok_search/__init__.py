"""grok_search package."""

from __future__ import annotations

__all__ = ["mcp"]


def __getattr__(name: str):
    # 延迟导入，避免 `python -m grok_search.server` 时触发模块重复加载告警。
    if name == "mcp":
        from .server import mcp
        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
