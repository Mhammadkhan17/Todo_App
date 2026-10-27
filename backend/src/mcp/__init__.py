from typing import Any

__all__ = ["create_server"]


def __getattr__(name: str) -> Any:
    # Lazy export so `python -m src.mcp.server` does not import the module
    # twice (runpy warns when the module is already in sys.modules).
    if name == "create_server":
        from .server import create_server

        return create_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
