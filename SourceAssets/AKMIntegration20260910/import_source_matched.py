import unreal,json
from pathlib import Path
O=Path(__file__).parent/'SourceMatched';dest='/Game/Weapons/AKMIntegration/SourceMatched'
old=unreal.load_asset('/Game/Weapons/AKMReplacement/HandsRepair/SK_AKM_HandsRepair');m4=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=m4.skeleton
t=unreal.AssetImportTask();t.filename=str(O/'SK_AKM_MannyNative.fbx');t.destination_path=dest;t.destination_name='SK_AKM_MannyNative';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);mesh=unreal.load_asset(dest+'/SK_AKM_MannyNative');assert mesh and mesh.skeleton==m4.skeleton
bindings={str(s.material_slot_name):s.material_interface for a in [old,m4] for s in a.get_editor_property('materials')};slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
 name=str(s.material_slot_name);mat=bindings.get(name)
 if not mat:
  matches=[v for k,v in bindings.items() if name.startswith(k) or k.startswith(name)];assert len(matches)==1,(name,list(bindings));mat=matches[0]
 s.material_interface=mat;slots[i]=s
mesh.set_editor_property('materials',slots);assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
report={'mesh':mesh.get_path_name(),'clips':{}}
for f in O.glob('A_AKM_*.fbx'):
 t=unreal.AssetImportTask();t.filename=str(f);t.destination_path=dest;t.destination_name=f.stem;t.automated=True;t.replace_existing=True;t.save=True
 opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;opt.skeleton=m4.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120);t.options=opt
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(dest+'/'+f.stem);assert a;a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False);report['clips'][f.stem]=a.get_play_length()
(O/'import.json').write_text(json.dumps(report,indent=2));unreal.log('AKM_NATIVE_IMPORT_PASS')

