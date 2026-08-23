"""User-site hook for pip on images that already define sitecustomize."""

import os

os.environ.setdefault("PIP_BREAK_SYSTEM_PACKAGES", "1")

