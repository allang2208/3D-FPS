"""Enable the existing skeletal asset's reimport flag, then save the V9 shapes."""
from pathlib import Path
import unreal as u,json
r=Path(__file__).resolve().parent
path='/Game/Weapons/M249/SK_M249_V7'
mesh=u.load_asset(path)
slots={str(s.material_slot_name):s.material_interface for s in mesh.materials}
mesh.get_editor_property('asset_import_data').set_editor_property('import_morph_targets',True)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.create_physics_asset=False
opt.skeleton=mesh.skeleton
data=opt.skeletal_mesh_import_data
data.set_editor_property('import_morph_targets',True)
data.set_editor_property('update_skeleton_reference_pose',False)
data.set_editor_property('use_t0_as_ref_pose',False)
data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
t=u.AssetImportTask();t.filename=str(r.parent/'Exports/SK_M249_V7.fbx');t.destination_path='/Game/Weapons/M249';t.destination_name='SK_M249_V7'
t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt;t.factory=u.FbxFactory()
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);t.get_objects()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
mesh=u.load_asset(path);bindings=mesh.materials
for i,s in enumerate(bindings):s.material_interface=slots[str(s.material_slot_name)];bindings[i]=s
mesh.set_editor_property('materials',bindings)
morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
(r/'import_receipt.json').write_text(json.dumps(dict(mesh=path,morphs=morphs),indent=2))
if not any(n.startswith('JC_Pose_') for n in morphs):raise RuntimeError('V9 morphs missing: '+str(morphs))
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('M249 mesh save failed')
print('M249_REPAIR03_SAVED',len(morphs),flush=True)
