"""Pytest bootstrap for the NikkoParse test suite.

The application modules use absolute imports (``from core... import ...``),
which only resolve when the repository root is on ``sys.path``. Pytest
inserts this ``tests/`` directory into ``sys.path``, not the repo root,
so the root is added here.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
