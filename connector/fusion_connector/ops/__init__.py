"""Importing this package fills OPS (core + build categories, builder.* from the installed skill)."""
from .base import OPS, OpError  # noqa: F401
from . import core, build, visual, scene, cache, layout, recover  # noqa: F401
import os as _os
if _os.environ.get("FUSION_MCP_TEST_FAULTS") == "1":   # fault-injection ops for the offline tests (refuse to run on a real Resolve)
    from .. import testkit  # noqa: F401
