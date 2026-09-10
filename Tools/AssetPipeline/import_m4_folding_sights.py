import unreal,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909');DEST='/Game/Weapons/M4FoldingSights'
old=unreal.load_asset('/Game/Weapons/M4EmptyReload/SK_M4_Infima_BoltReceiver');assert old
materials={str(m.material_slot_name):m.material_interface for m in old.materials}
def imp(name,skeletal):
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else unreal.FBXImportType.FBXIT_STATIC_MESH
 o.import_as_skeletal=skeletal;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
 if skeletal:o.skeleton=old.skeleton
 else:o.static_mesh_import_data.combine_meshes=True
 t=unreal.AssetImportTask();t.filename=str(OUT/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True;t.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert t.imported_object_paths
 mesh=unreal.load_asset(DEST+'/'+name);assert mesh
 if skeletal:
  assert mesh.skeleton==old.skeleton
  slots=mesh.materials
  for i,m in enumerate(slots):m.material_interface=materials[str(m.material_slot_name)];slots[i]=m
  mesh.set_editor_property('materials',slots)
 else:
  for i,m in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(m.material_slot_name)])
 unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
 return mesh
imp('SK_M4_FoldingSights',True)
for name in ['Rear','Front']:imp('SM_M4_'+name+'Sight',False)
unreal.log('M4_FOLDING_IMPORT_PASS')
