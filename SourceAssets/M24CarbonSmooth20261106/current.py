from pathlib import Path
import unreal as u,json,hashlib
O=Path(__file__).resolve().parent
E=u.EditorAssetLibrary
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
rows={}
for kind in ('Native','Advanced'):
    path='/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_'+kind
    obj=u.load_asset(path)
    if not obj or path in dirty:raise RuntimeError('Unavailable/unsaved target: '+path)
    file=Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
    rows[kind.lower()]={'path':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in obj.static_materials},
        'edition':E.get_metadata_tag(obj,'M24CarbonSpineEdition')}
(O/'current.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('M24_SOURCE_ASSETS',rows)
