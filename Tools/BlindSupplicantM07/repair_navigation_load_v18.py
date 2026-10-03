"""Save M07's authored tiles without discarding them on each map load."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'BodyMotionV18/NavigationLoadRepair'
REPORT = OUT / 'ue_navigation_load_repair_v18.json'
MAP = '/Game/GameMaps/DayNight_Lighting'

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use the guarded background producer after the editor exits.')
OUT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup = OUT / ('DayNight_Lighting.before-navigation-load-repair-' + stamp + '.umap')
shutil.copy2(PROJECT / 'Content/GameMaps/DayNight_Lighting.umap', backup)
report = json.loads(u.BlindSupplicantNavigationRepairV08.build_and_save_map_navigation(MAP))
report.update(revision='BodyMotionV18NavigationLoadRepair', backup=str(backup),
              cause='The M07 actor saved force_rebuild_on_load=true. Map reload discarded saved tiles and rebuilt them for 395.35 seconds during the user session.',
              runtime_tested=False, visual_tested=False, tested=False, user_review_pending=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
if not report.get('saved') or not report.get('navigation_built'):
    raise RuntimeError('M07 navigation production did not save: ' + json.dumps(report, ensure_ascii=False))
for name in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT / name
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(navigation_load_repair_saved=True, navigation_load_repair_receipt=str(REPORT),
                  navigation=report, stage='V18 pose-baked locomotion and M07 navigation load repair saved',
                  runtime_tested=False, visual_tested=False, tested=False, user_review_pending=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V18_NAVIGATION_LOAD_REPAIR_SAVED ' + str(REPORT), flush=True)
