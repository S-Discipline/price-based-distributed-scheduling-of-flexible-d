"""Delegate to the system pip with Debian's PEP 668 override enabled."""

from __future__ import annotations

import os
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parent.parent
os.environ.setdefault("PIP_BREAK_SYSTEM_PACKAGES", "1")

# Stop this repository-local shim from shadowing the actual pip package when we
# delegate. Empty sys.path entries also resolve to the current working directory.
sys.path = [
    entry for entry in sys.path
    if Path(entry or os.getcwd()).resolve() != repo_root
]
sys.modules.pop("pip", None)

from pip._internal.cli.main import main  # noqa: E402

raise SystemExit(main())

