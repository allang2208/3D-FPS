"""Import the M16 mesh and private animation set inside the running editor."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
D='/Game/Weapons/M16A2/Gameplay20260919'
reload_only=globals().get('M16_RELOAD_ONLY',False)
empty_only=globals().get('M16_EMPTY_ONLY',False)
reload_only=reload_only or empty_only
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Exit PIE before importing M16 assets; UE cannot replace skeletal meshes in play mode.')
tools=u.AssetToolsHelpers.get_asset_tools()
reference=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings={str(s.material_slot_name):s.material_interface for s in reference.materials}
gun_material=u.load_asset('/Game/Weapons/M16A2Migration/Materials/M_M16A2_PBR')
def do_import(name,animation=False,skeleton=None):
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=not animation;options.import_mesh=not animation;options.import_animations=animation
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    if skeleton:options.skeleton=skeleton
    if animation:
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    else:
        options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        options.skeletal_mesh_import_data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',True)
    task=u.AssetImportTask();task.filename=str(O/'Export'/f'{name}.fbx')
    task.destination_path=D+('/Animations' if animation else '');task.destination_name=name
    task.options=options;task.automated=True;task.replace_existing=True;task.save=False
    tools.import_asset_tasks([task])
    asset=u.load_asset(task.destination_path+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
previous=u.load_asset(D+'/SK_M16_Manny')
if reload_only:
    mesh=previous
else:
    mesh=do_import('SK_M16_Manny',skeleton=previous.skeleton if previous else None)
    slots=mesh.materials
    for i,slot in enumerate(slots):
        name=str(slot.material_slot_name)
        slot.material_interface=gun_material if name.startswith('M_M16_') else bindings[name]
        slots[i]=slot
    mesh.set_editor_property('materials',slots)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('M16 mesh save failed')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
clips={}
for file in sorted((O/'Export').glob('A_M16_*.fbx')):
    if empty_only and file.stem!='A_M16_reload_empty':continue
    if reload_only and file.stem not in ['A_M16_reload','A_M16_reload_empty']:continue
    a=do_import(file.stem,True,mesh.skeleton)
    a.set_editor_property('bone_compression_settings',compression)
    if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('M16 animation save failed: '+file.stem)
    clips[file.stem]={'path':a.get_path_name(),'duration':a.get_play_length()}
if not reload_only:u.EditorAssetLibrary.save_loaded_asset(mesh.skeleton,False)
(O/('empty_reload_import_result.json' if empty_only else 'reload_import_result.json' if reload_only else 'import_result.json')).write_text(json.dumps({'mesh':mesh.get_path_name(),'clips':clips},indent=2))
u.log('M16_EMPTY_RELOAD_IMPORT_COMPLETE' if empty_only else 'M16_RELOAD_IMPORT_COMPLETE' if reload_only else 'M16_GAMEPLAY_IMPORT_COMPLETE')
