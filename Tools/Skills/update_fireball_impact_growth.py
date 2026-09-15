"""Apply radius growth to the existing impact Niagara system; authoring only.

Run through UnrealEditor-Cmd -run=pythonscript -unattended -multiprocess -NullRHI.
Reuses installed materials and audio without rebuilding them or launching play.
"""
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(u.Paths.project_dir()) / 'Tools/Skills'))
from build_fireball_impact_realistic import DEST, explosion


def build():
    materials = [u.load_asset(DEST + '/' + name) for name in
                 ['MI_ImpactCombustion', 'MI_ImpactThinSmoke', 'M_ImpactEmber']]
    if not all(materials):
        raise RuntimeError('Restore the existing fireball impact materials before applying growth.')
    explosion(*materials)
    u.log('FIREBALL_IMPACT_RADIUS_GROWTH_SAVED')


if __name__ == '__main__':
    build()
