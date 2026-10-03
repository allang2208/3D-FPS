"""Build/save M07 navigation in the existing map, without gameplay or queries.

Run only through the project's guarded background importer after its Editor
module containing BlindSupplicantNavigationRepairV08 has been compiled.
The legacy navigation receipt was satisfied by an actor's presence; this
producer requires actual tile output before it saves the package.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUTPUT = ROOT / 'RecoveryOriginalV08/navigation'
MAP = '/Game/GameMaps/DayNight_Lighting'


def produce():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        raise RuntimeError('Use the guarded M07 background commandlet after the editor has exited.')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    map_file = PROJECT / 'Content/GameMaps/DayNight_Lighting.umap'
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = OUTPUT / ('DayNight_Lighting.before-v08-navigation-' + stamp + '.umap')
    shutil.copy2(map_file, backup)
    receipt = json.loads(u.BlindSupplicantNavigationRepairV08.build_and_save_map_navigation(MAP))
    receipt['backup'] = str(backup)
    receipt['runtime_tested'] = False
    path = OUTPUT / 'navigation_delivery_original_v08.json'
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('M07_ORIGINAL_V08_NAVIGATION ' + json.dumps(receipt, ensure_ascii=False))
    if not receipt.get('saved') or not receipt.get('navigation_built'):
        raise RuntimeError('M07 navigation production did not save: ' + json.dumps(receipt, ensure_ascii=False))
    # Update only this task's navigation section, retaining concurrently made
    # model/material/animation records. No success is inferred from old data.
    gameplay_path = ROOT / 'gameplay_delivery.json'
    if gameplay_path.exists():
        gameplay = json.loads(gameplay_path.read_text(encoding='utf-8'))
        gameplay['navigation'] = receipt
        gameplay_path.write_text(json.dumps(gameplay, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


if __name__ == '__main__':
    produce()
