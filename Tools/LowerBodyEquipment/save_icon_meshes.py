"""Save front-facing trousers and a single three-quarter sneaker for UI icons.

Only display geometry changes. Wearable meshes, pickup pairs and native material
instances remain the source. The inverse catalog rotation preserves saved item
snapshots that already reference these display assets and camera parameters.
"""
import json
from pathlib import Path
import unreal as u
# LevelEditor has no live editor instance in a Python commandlet.
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level_editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level_editor and level_editor.is_in_play_in_editor():
        raise RuntimeError('End the current play session before saving equipment icon assets')
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LowerBodyEquipment20261003'
saved=json.loads((R/'saved_assets.json').read_text())
for key in ['jeans','cargo','sneakers']:
    mesh=u.load_asset(saved[key]);G=u.GeometryScript_AssetUtils
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read icon mesh')
    transforms=u.GeometryScript_MeshTransforms
    if key=='sneakers':
        # Each shoe is a separate shell. Keep the positive-X shoe in its entirety.
        remove=[]
        for ti in range(dm.get_triangle_count()):
            valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
            if valid and a.x+b.x+c.x<0:remove.append(ti)
        u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False)
        # Toe toward the lower left, upper facing the camera; preserve proportions.
        transforms.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0))
        transforms.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
        transforms.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=-18,yaw=-60,roll=0)))
    else:
        # The wearer faces +Y; the shared equipment camera originally saw the back.
        transforms.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
    path='/Game/Characters/ModularOutfit20260924/LowerBodyEquipment20261003/Icons/SM_'+key.title()+'_Display'
    opts=u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False)
    icon=u.load_asset(path)
    if icon:_,status=G.copy_mesh_to_static_mesh(dm,icon,u.GeometryScriptCopyMeshToAssetOptions(),u.GeometryScriptMeshWriteLOD())
    else:icon,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author icon mesh')
    for i,m in enumerate(mesh.materials):icon.set_material(i,m.material_interface)
    if not u.EditorAssetLibrary.save_loaded_asset(icon,False):raise RuntimeError('Cannot save icon mesh: '+key)
    saved[key+'_icon_mesh']=icon.get_path_name()
(R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
print('LOWER_BODY_ICON_MESHES_SAVED',flush=True)
