"""Make the fixed pip command compatible with OpenResearch's Debian image.

Python imports this module automatically from the committed working directory.
The setting is scoped to the ephemeral experiment process and is the environment
variable equivalent of pip's documented ``--break-system-packages`` option.
"""

import os

os.environ.setdefault("PIP_BREAK_SYSTEM_PACKAGES", "1")

