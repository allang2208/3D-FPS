import unreal,json
from pathlib import Path
O=Path(__file__).parent;dest='/Game/Weapons/AKMIntegration'
old=unreal.load_asset('/Game/Weapons/AKMReplacement/HandsRepair/SK_AKM_HandsRepair')
m4=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=old.skeleton
t=unreal.AssetImportTask();t.filename=str(O/'SK_AKM_SharedArms.fbx');t.destination_path=dest;t.destination_name='SK_AKM_SharedArms';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);mesh=unreal.load_asset(dest+'/SK_AKM_SharedArms');assert mesh and mesh.skeleton==old.skeleton
bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
bindings.update({str(s.material_slot_name):s.material_interface for s in m4.get_editor_property('materials')})
slots=mesh.get_editor_property('materials');report=[]
for i,s in enumerate(slots):
 name=str(s.material_slot_name)
 mat=bindings.get(name)
 if not mat:
  matches=[v for k,v in bindings.items() if k.startswith(name) or name.startswith(k)]
  assert len(matches)==1,(name,list(bindings));mat=matches[0]
 s.material_interface=mat;slots[i]=s;report.append({'slot':name,'material':mat.get_path_name()})
mesh.set_editor_property('materials',slots);assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'materials':report},indent=2));unreal.log('AKM_SHARED_ARMS_IMPORT_PASS')
