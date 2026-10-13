import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
SOURCE=ROOT/'SourceAssets/WoodworkingBenchV5Clean20261012'
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'Saved/WoodworkingClearTable20261012/ImportHost').resolve():
    raise RuntimeError('Use isolated import host')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
receipt=json.loads((SOURCE/'import_receipt.json').read_text())
for record in receipt['meshes']:
    mesh=u.load_asset(record['mesh']);mesh.modify()
    if not sub.set_lod_screen_sizes(mesh,[1,.45,.18]):raise RuntimeError('LOD screen-size assignment failed')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('LOD final save failed')
    record['lod_screen_sizes']=list(sub.get_lod_screen_sizes(mesh))
receipt['lod_screen_sizes_set_after_final_mesh_build']=True
(SOURCE/'import_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
print('WOODWORKING_LOD_SAVED')
