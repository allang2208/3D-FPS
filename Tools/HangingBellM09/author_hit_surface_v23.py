import unreal as u,json,shutil,traceback
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23')
path='/Game/Monsters/HangingBellM09/V23/PA_M09_HitSurface'
A=u.EditorAssetLibrary
report={'complete':False,'saved':[],'game_tested':False}
try:
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:raise RuntimeError('Preserve unsaved hit asset')
    mesh=u.load_asset('/Game/Monsters/HangingBellM09/V04/SK_M09');asset=u.load_asset(path)
    original=mesh.physics_asset.get_path_name();skeleton=mesh.skeleton.get_path_name()
    source=Path('D:/FPS3D/FPSGAME/Content/Monsters/HangingBellM09/V23/PA_M09_HitSurface.uasset')
    backup=OUT/'Before/PA_M09_HitSurface.uasset'
    if not backup.exists():shutil.copy2(source,backup)
    if not u.HangingBellM09.build_hit_surface_physics(mesh,asset):raise RuntimeError('Could not author all 24 membrane query bodies')
    A.set_metadata_tag(asset,'M09HitSurfaceRevision','V23 six membranes with four animated query segments; original corpse asset preserved')
    if not A.save_loaded_asset(asset,False):raise RuntimeError('Could not save authored hit physics')
    report.update({'complete':True,'saved':[asset.get_path_name()],'corpse_physics':original,'skeleton':skeleton,'body_segments':24,'original_mesh_saved':False})
except Exception:
    report['error']=traceback.format_exc()
    raise
finally:
    (OUT/'Records/authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M09_HIT_SURFACE_AUTHORED '+json.dumps(report))
