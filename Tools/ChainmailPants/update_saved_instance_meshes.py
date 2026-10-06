"""Update the two V1 static paths retained by already-saved item snapshots.

Wearable V2 resources are separate. This scoped asset update keeps existing
inventory/dropped instances current without editing the player's save data.
"""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2'
new=json.loads((R/'saved_assets.json').read_text())
old=json.loads((R.parent/'saved_assets.json').read_text())
G=u.GeometryScript_AssetUtils;E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('Cannot update item meshes during play')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved={}
for key in ['icon','pickup']:
    source=u.load_asset(new[key]);target=u.load_asset(old[key])
    if not source or not target:raise RuntimeError('Missing scoped item mesh '+key)
    dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+new[key])
    slots=source.get_editor_property('static_materials')
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[x.material_interface for x in slots],
        new_material_slot_names=[str(x.material_slot_name) for x in slots],enable_recompute_normals=False,enable_recompute_tangents=True)
    _,status=G.copy_mesh_to_static_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot update '+old[key])
    options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;rows=[]
    for ratio,screen in [(1.,1.),(.55,.18),(.3,.07)]:
        row=u.StaticMeshReductionSettings();row.percent_triangles=ratio;row.screen_size=screen;rows.append(row)
    options.reduction_settings=rows;sub.set_lods(target,options)
    target.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([target.get_outer()],False) or E.save_loaded_asset(target,False)):
        raise RuntimeError('Could not save '+old[key])
    saved[key]=target.get_path_name()
(R/'existing-instance-assets-saved.json').write_text(json.dumps(saved,indent=2))
print('CHAINMAIL_EXISTING_INSTANCE_MESHES_UPDATED',flush=True)
