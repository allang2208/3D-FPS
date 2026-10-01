"""Compatibility entry for the current electrical flux-beam author.

The retired smooth cylinder/coil packages are archived under project trash.
Runtime now uses ThunderFluxV3; no play, render or acceptance tests.
"""
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(u.Paths.project_dir()) / 'Tools/Skills'))
from build_thunder_flux_v3 import build_flux


def build_column():
    return build_flux()


if __name__ == '__main__':
    build_column()
