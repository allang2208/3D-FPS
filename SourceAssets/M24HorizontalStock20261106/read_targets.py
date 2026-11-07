"""Capture only the two stock assets that this revision replaces."""
from pathlib import Path
import unreal as u,json,hashlib
O=Path(__file__).resolve().parent
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
rows={}
for kind in ('Native','Advanced'):
    p='/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_'+kind
    if p in dirty:raise RuntimeError('Unsaved target retained '+p)
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    f=Path(u.Paths.project_content_dir())/(p[6:]+'.uasset')
    rows[kind.lower()]={'path':p,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in a.static_materials}}
(O/'current.json').write_text(json.dumps(rows,indent=2))
print('M24_HORIZONTAL_TARGETS_CAPTURED',list(rows))
