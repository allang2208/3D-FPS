"""Rebuild only the active V12 garments with bone-local collision dimensions."""
from pathlib import Path
import hashlib,json,shutil
import unreal as u

project=Path('D:/FPS3D/FPSGAME')
out=project/'SourceAssets/BoundCongregateMeshy20261006/GarmentRepairV13';out.mkdir(exist_ok=True)
path='/Game/Monsters/BoundCongregate/SurfaceFitV12/SK_BoundCongregate_SurfaceFitV12'
file=project/'Content/Monsters/BoundCongregate/SurfaceFitV12/SK_BoundCongregate_SurfaceFitV12.uasset'
report={'revision':'GarmentRepairV13','saved':False,'gameplay_tested':False,'mesh':path,'change':'Convert mesh-space capsule radius and length to bone-local units; preserve geometry, weights, materials, animation and corpse.'}
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is running; retain the current game')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:raise RuntimeError('Retain unsaved mesh changes')
    cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
    mesh=cdo.get_editor_property('visual_mesh')
    if mesh.get_path_name()!=path+'.SK_BoundCongregate_SurfaceFitV12':raise RuntimeError('Active mesh changed; retain it')
    before=out/'before';before.mkdir(exist_ok=True);backup=before/file.name
    if not backup.exists():shutil.copy2(file,backup)
    report['backup']=str(backup);report['before_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest()
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    mesh.modify()
    if not u.BoundCongregate.build_garment_simulation(mesh):raise RuntimeError('Garment build failed')
    u.EditorAssetLibrary.set_metadata_tag(mesh,'ClothCollisionRevision','V13-bone-local-capsule-dimensions')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
    u.SystemLibrary.execute_console_command(None,'BoundCongregate.DescribeGarments '+mesh.get_path_name()+' '+str(out/'garment-data-saved.txt'))
    report.update(saved=True,after_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    print('BOUND_CONGREGATE_GARMENT_SCALE_V13_SAVED',flush=True)
finally:
    (out/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')
