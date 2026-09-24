import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import restore_wall_relief
import restore_concrete_wall
restore_wall_relief.install()
restore_concrete_wall.install()
