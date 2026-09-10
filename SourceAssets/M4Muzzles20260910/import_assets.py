import unreal,json,shutil,os
from pathlib import Path
OUT=Path(__file__).parent;DEST='/Game/Weapons/M4MuzzlesV1';lib=unreal.MaterialEditingLibrary
source=unreal.load_asset('/Game/Weapons/M4InfimaV3/Flash_Hider_001');assert source
base=source
while isinstance(base,unreal.MaterialInstanceConstant):base=base.get_editor_property('parent')
assert isinstance(base,unreal.Material)
def variant(name,color):
 parent=unreal.load_asset(DEST+'/M_'+name)
 if not parent:parent=unreal.EditorAssetLibrary.duplicate_asset(base.get_path_name(),DEST+'/M_'+name)
 if not unreal.load_asset(DEST+'/MI_'+name):
  node=lib.get_material_property_input_node(parent,unreal.MaterialProperty.MP_BASE_COLOR)
  output=lib.get_material_property_input_node_output_name(parent,unreal.MaterialProperty.MP_BASE_COLOR)
  tint=lib.create_material_expression(parent,unreal.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','MuzzleFinishTint');tint.set_editor_property('default_value',unreal.LinearColor(*color,1))
  mul=lib.create_material_expression(parent,unreal.MaterialExpressionMultiply);lib.connect_material_expressions(node,output,mul,'A');lib.connect_material_expressions(tint,'',mul,'B');lib.connect_material_property(mul,'',unreal.MaterialProperty.MP_BASE_COLOR);lib.recompile_material(parent)
  instance=unreal.EditorAssetLibrary.duplicate_asset(source.get_path_name(),DEST+'/MI_'+name)
  if isinstance(instance,unreal.MaterialInstanceConstant):instance.set_editor_property('parent',parent)
  else:instance=parent
  unreal.EditorAssetLibrary.save_loaded_asset(parent,only_if_is_dirty=False);unreal.EditorAssetLibrary.save_loaded_asset(instance,only_if_is_dirty=False)
 else:instance=unreal.load_asset(DEST+'/MI_'+name)
 return instance
dark=variant('MuzzleRecess',(.55,.55,.55));gold=variant('TitaniumTrim',(1.1,.78,.36))
report={'source_material':source.get_path_name(),'parent_material':base.get_path_name(),'assets':{}}
for key in ['suppressor','brake','titanium_brake']:
 name='SM_M4_'+key;o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;o.import_as_skeletal=False;o.import_materials=False;o.import_textures=False;o.static_mesh_import_data.combine_meshes=True
 task=unreal.AssetImportTask();task.filename=str(OUT/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True;task.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=unreal.load_asset(DEST+'/'+name);assert mesh
 for i,s in enumerate(mesh.static_materials):mesh.set_material(i,gold if 'Titanium' in str(s.material_slot_name) else dark if 'Recess' in str(s.material_slot_name) else source)
 assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
 b=mesh.get_bounds();report['assets'][key]={'asset':mesh.get_path_name(),'origin':[b.origin.x,b.origin.y,b.origin.z],'extent':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]}
src=Path(os.environ.get('GODOT_SOURCE_ROOT','E:/3d/trash/e-drive-repositories-20260910/3d/3-dfps'))/'assets/sfx/suppressor'
if src.is_dir():
 shutil.copy2(src/'SOURCE.md',OUT/'SUPPRESSOR_AUDIO_SOURCE.md');shutil.copy2(src/'akm_recorded_shot.wav',OUT/'S_M4_Suppressed.wav')
assert (OUT/'S_M4_Suppressed.wav').is_file() and (OUT/'SUPPRESSOR_AUDIO_SOURCE.md').is_file(), 'Restore the licensed audio or set GODOT_SOURCE_ROOT.'
t=unreal.AssetImportTask();t.filename=str(OUT/'S_M4_Suppressed.wav');t.destination_path=DEST;t.destination_name='S_M4_Suppressed';t.automated=True;t.replace_existing=True;t.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert unreal.load_asset(DEST+'/S_M4_Suppressed')
(OUT/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8');unreal.log('M4_MUZZLES_IMPORT_PASS')
