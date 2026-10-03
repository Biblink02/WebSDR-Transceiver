import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for directory in ('shared', 'backend-controller', 'sdr-server', 'tools'):
    sys.path.insert(0, str(ROOT/directory))
os.environ['CONFIG_PATH'] = str(ROOT/'config/config.yaml')
