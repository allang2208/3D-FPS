"""Import the P9-derived M1911 and retain the game's existing material assets."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/M1911/P9Retarget20260913'
assets=u.AssetToolsHelpers.get_asset_tools()
old=u.load_asset('/Game/Weapons/M1911/Integrated20260913/SK_M1911_Manny')
arms=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings={str(s.material_slot_name):s.material_interface for s in old.materials}
bindings.update({str(s.material_slot_name):s.material_interface for s in arms.materials})
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
opt.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
t=u.AssetImportTask();t.filename=str(O/'SK_M1911_Manny.fbx');t.destination_path=P;t.destination_name='SK_M1911_Manny';t.options=opt;t.automated=True;t.replace_existing=True;t.save=True
assets.import_asset_tasks([t]);mesh=u.load_asset(P+'/SK_M1911_Manny')
slots=mesh.materials
for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
mesh.set_editor_property('materials',slots);u.EditorAssetLibrary.save_loaded_asset(mesh,False)
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
clips={}
for source in sorted(O.glob('A_M1911_*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    t=u.AssetImportTask();t.filename=str(source);t.destination_path=P+'/Animations';t.destination_name=source.stem;t.options=opt;t.automated=True;t.replace_existing=True;t.save=True
    assets.import_asset_tasks([t]);clip=u.load_asset(P+'/Animations/'+source.stem)
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(clip,False);clips[source.stem]=clip.get_path_name()
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'animations':clips,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'state':'Imported; runtime testing not performed'},indent=2),encoding='utf-8')
u.log('M1911_P9_IMPORT_COMPLETE')
