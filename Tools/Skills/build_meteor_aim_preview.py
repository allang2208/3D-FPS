"""Compatibility entry for the current surface-aligned Meteor preview author."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_meteor_surface_preview import build

if __name__ == '__main__':
    build()
