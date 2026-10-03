"""Save upright display meshes from the same fitted wearable geometry."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LowerBodyEquipment20261003'
saved=json.loads((R/'saved_assets.json').read_text())
for key in ['jeans','cargo','sneakers']:
    mesh=u.load_asset(saved[key]);G=u.GeometryScript_AssetUtils
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read icon mesh')
    path='/Game/Characters/ModularOutfit20260924/LowerBodyEquipment20261003/Icons/SM_'+key.title()+'_Display'
    opts=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False)
    icon=u.load_asset(path)
    if icon:_,status=G.copy_mesh_to_static_mesh(dm,icon,u.GeometryScriptCopyMeshToAssetOptions(),u.GeometryScriptMeshWriteLOD())
    else:icon,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author icon mesh')
    for i,m in enumerate(mesh.materials):icon.set_material(i,m.material_interface)
    if not u.EditorAssetLibrary.save_loaded_asset(icon,False):raise RuntimeError('Cannot save icon mesh')
    saved[key+'_icon_mesh']=icon.get_path_name()
(R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
print('LOWER_BODY_ICON_MESHES_SAVED',flush=True)
