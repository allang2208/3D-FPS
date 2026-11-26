"""Legacy entrypoint for the corrected native Body cuff producer."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat3_fp import build
build('Body')
