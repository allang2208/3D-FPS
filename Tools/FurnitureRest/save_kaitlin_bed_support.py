"""Save the native female arm refinement in new packages, then reread both bodies."""
import json,runpy
from pathlib import Path
import unreal as u
REVISION=globals().get('FURNITURE_REVISION','MeshyBedSupportedHands20261024')
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022')/REVISION
read=lambda p:json.loads(p.read_text());data=read(OUT/'kaitlin_corrected_arms.json');saved=read(OUT/'assets_saved.json');E=u.EditorAssetLibrary;updates={}
for role,take in data['clips'].items():
    source=u.load_asset(take['source']);destination='/Game/Characters/KaitlinPlayer20261023/'+REVISION+'/NativePalmContact/'+source.get_name()
    if E.does_asset_exist(destination):raise RuntimeError('Preserve existing candidate: '+destination)
    clip=E.duplicate_asset(take['source'],destination);ctl=clip.get_editor_property('controller');ctl.open_bracket('Native planted palms',False)
    try:
        for i,name in enumerate(data['names']):
            keys=[f[i] for f in take['frames']]
            if not ctl.set_bone_track_keys(name,[u.Vector(*p[:3]) for p in keys],[u.Quat(*p[3:7]) for p in keys],[u.Vector(*p[7:]) for p in keys],False):raise RuntimeError(name)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip,False):raise RuntimeError('Native support save failed')
    updates[role]=clip.get_path_name()
saved['variants']['kaitlin'].update(updates);saved['variant_refinements']={'kaitlin':str(OUT/'kaitlin_corrected_arms.json')}
(OUT/'assets_saved.json').write_text(json.dumps(saved,indent=2));(OUT/'native_palm_save.json').write_text(json.dumps(updates,indent=2))
runpy.run_path(str(Path(__file__).with_name('read_meshy_bed_saved.py')),init_globals={'FURNITURE_REVISION':REVISION})
print('KAITLIN_NATIVE_PALMS_SAVED')
