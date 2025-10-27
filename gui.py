#!/usr/bin/env python3
"""Launch Forest Change Framework GUI."""

import sys

try:
    from src.forest_change_framework.gui.app import main
    main()
except ImportError:
    # Try alternate import path
    from forest_change_framework.gui.app import main
    main()
