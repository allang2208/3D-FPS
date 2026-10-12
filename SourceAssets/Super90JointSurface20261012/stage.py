import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from ue_pipeline import stage
stage()
