"""Hardknuckle cuff repair entry point.

The retired whole-mesh winding rewrite inverted every original glove face.
Use intact native glove geometry and per-profile closed wrist liners instead.
Refresh HardKnuckleRepair20261017/read_sources.py exports if native skin changes.
"""
import sys
from pathlib import Path
REPAIR=Path(__file__).parent.parent / "HardKnuckleRepair20261017"
sys.path.insert(0,str(REPAIR))
from author import main
from publish_sources import publish

if __name__ == "__main__":
    main()
    publish(require_saved=False)
