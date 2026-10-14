"""Canonical Dragon Breath authoring entrypoint (Niagara Fluids Volume V8).

Run in SourceAssets/DragonBreath20261013/AuthorHost. The accepted original
fireball and campfire remain unchanged; rejected Sprite versions are archived
under trash/magic-closeout-20261014 (see the publication archive manifest).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_dragon_breath_volume import *

if __name__ == '__main__':
    run()
