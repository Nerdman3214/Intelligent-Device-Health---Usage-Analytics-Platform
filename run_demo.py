#!/usr/bin/env python3
"""
Quick Demo Runner

Run this to see the complete Phase 1 + Phase 2 system in action.
"""

import sys
from pathlib import Path

# Add python directory to path
project_root = Path(__file__).parent
python_dir = project_root / 'python'
sys.path.insert(0, str(python_dir))

# Import and run demo
from demo import demo_complete_workflow

if __name__ == '__main__':
    demo_complete_workflow()
