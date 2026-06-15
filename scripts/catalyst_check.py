#!/usr/bin/env python3
"""
Catalyst tracker CLI.

Usage:
  python scripts/catalyst_check.py                              # show all
  python scripts/catalyst_check.py --pending                   # pending only
  python scripts/catalyst_check.py --fired                     # fired only
  python scripts/catalyst_check.py --fire  PCB "GB300/Rubin放量" "confirmed in Q2 earnings"
  python scripts/catalyst_check.py --miss  PCB "GB300/Rubin放量" "pushed to H2"
  python scripts/catalyst_check.py --reset PCB "GB300/Rubin放量"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.catalyst_tracker import fire, miss, reset, print_dashboard

args = sys.argv[1:]

if not args:
    print_dashboard()
elif args[0] == "--pending":
    print_dashboard(filter_status="pending")
elif args[0] == "--fired":
    print_dashboard(filter_status="fired")
elif args[0] == "--fire" and len(args) >= 3:
    notes = args[3] if len(args) > 3 else ""
    fire(args[1], args[2], notes)
    print_dashboard()
elif args[0] == "--miss" and len(args) >= 3:
    notes = args[3] if len(args) > 3 else ""
    miss(args[1], args[2], notes)
    print_dashboard()
elif args[0] == "--reset" and len(args) >= 3:
    reset(args[1], args[2])
    print_dashboard()
else:
    print(__doc__)
    sys.exit(1)
