#!/usr/bin/env python3
"""Platform Test Suite Runner.

Executes all unit, integration, and security guardrail tests across all components:
- Piece 1: FastMCP Server & Synthetic Data (mcp_server)
- Piece 2: Custom Governed ADK Agent (agent)
- Piece 3: Gateway & Policy Simulator (gateway)
- Piece 4: Interactive Visual UI: Gateway Inspection Dashboard (ui)
"""

import sys
import unittest
from pathlib import Path

# Automatically ensure agents/platform/agent-gateway is on sys.path
_PLATFORM_DIR = Path(__file__).resolve().parent
if str(_PLATFORM_DIR) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_DIR))


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(_PLATFORM_DIR), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
