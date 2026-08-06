"""Central place to mute noisy third-party deprecation warnings in local dev."""

from __future__ import annotations

import warnings


def suppress_langchain_deprecation_warnings() -> None:
    """Mute LangChain/LangGraph deprecation noise during local dev."""
    try:
        from langchain_core._api import deprecation as lc_deprecation
        from langchain_core._api.deprecation import (
            LangChainDeprecationWarning,
            LangChainPendingDeprecationWarning,
        )
    except ImportError:
        return

    # LangGraph imports `langchain`, which re-enables these warnings via
    # surface_langchain_deprecation_warnings(). Disable that hook so our
    # ignore filters are not overridden mid-import.
    lc_deprecation.surface_langchain_deprecation_warnings = lambda: None

    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
