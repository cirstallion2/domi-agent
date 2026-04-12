import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from domi.orchestrator import load_config, run_scan_mode
cfg = load_config()
run_scan_mode(cfg)
