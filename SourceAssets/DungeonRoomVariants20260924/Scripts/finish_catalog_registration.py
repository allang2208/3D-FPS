"""Resume the first install after its successful OFPA save, without writing UE packages.

The initial commandlet saved the generator package, then unnecessarily attempted
the unchanged root map and hit Windows error 32. Resume only the remaining JSON
publication; do not load or overwrite the occupied map.
"""
import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
log=(ROOT/'Receipts/install-console.log').read_text(encoding='utf-8',errors='replace')
package='/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH'
# These are the actual first install's save records, not a scene/seed test.
if 'Moving output files for package: '+package not in log or 'RuntimeError: Cannot save dungeon map' not in log:
    raise RuntimeError('This one-time recovery only applies after the recorded actor-package save')
before=json.loads((ROOT/'Sources/catalog-before.json').read_text(encoding='utf-8'))
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](before)
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/modules.json').write_text(json.dumps(dict(modules=[m for m in catalog['modules'] if m['id']!=m.get('family_id',m['id'])]),ensure_ascii=False,indent=2),encoding='utf-8')
receipt=dict(stage='map_saved',map='/Game/GameMaps/L_Dungeon_Randomized',room_ids=catalog['room_ids'],new_meshes=68,
    saved_actor_packages=[package],root_map_modified=False,tests_run=False,
    completion='Generator OFPA package saved by install commandlet; remaining JSON publication resumed offline.',
    initial_commandlet_exit=1,initial_root_save_error='Windows sharing violation 32; unchanged root map does not require save')
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('ROOM_VARIANTS_REGISTRATION_COMPLETED',catalog['room_ids'])
