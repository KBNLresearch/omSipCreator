#! /usr/bin/env python
#
"""CLI wrapper script, ensures that relative imports work correctly in a PyInstaller build"""

from omSipCreator.omSipCreator import main

if __name__ == '__main__':
    main()
