"""Save Blizzard cloud height interpolation; no map load or gameplay run.

Use the existing editor bridge when open, otherwise the Python commandlet.
The shared StormDomain cloud, its material, and gathering cloud stay untouched.
"""
import importlib
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import build_rolling_storm_clouds as clouds


def run():
    global clouds
    clouds = importlib.reload(clouds)
    clouds.SOURCE = ROOT / 'SourceAssets/BlizzardVolume20261013'
    clouds.SOURCE.mkdir(parents=True, exist_ok=True)
    clouds.REPORT = {'revision': 'BlizzardVolume20261013', 'saved_assets': [],
                     'gameplay_tested': False, 'rendered': False}
    material = u.load_asset(clouds.DEST + '/M_RollingStormCloud')
    if not material:
        raise RuntimeError('Missing current rolling storm material')
    clouds.blizzard(material)
    clouds.REPORT.update(stage='assets_saved', max_visual_layers=3,
                         source_storm_modified=False, native_build_required=True)
    (clouds.SOURCE / 'asset-authoring.json').write_text(json.dumps(clouds.REPORT, indent=2), encoding='utf-8')
    print('BLIZZARD_VOLUME_ASSETS_SAVED ' + json.dumps(clouds.REPORT))


if __name__ == '__main__':
    run()
