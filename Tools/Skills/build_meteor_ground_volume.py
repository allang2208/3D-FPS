"""Current meteor ground-fire authoring entry; previous versions remain donors."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_meteor_ground_fire_v4 import run

if __name__ == '__main__':
    run()
