import unreal,json
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/PrismHandstopV1';lib=unreal.MaterialEditingLibrary
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;o.import_as_skeletal=False;o.import_materials=False;o.import_textures=False;o.static_mesh_import_data.combine_meshes=True
t=unreal.AssetImportTask();t.filename=str(P/'SM_PrismHandstop.fbx');t.destination_path=D;t.destination_name='SM_PrismHandstop';t.automated=True;t.replace_existing=True;t.save=True;t.options=o
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);mesh=unreal.load_asset(D+'/SM_PrismHandstop');assert mesh
materials=[]
for name,color,metal,rough in [('Prism_Polymer',(.028,.032,.039),.05,.68),('Prism_Saddle',(.09,.10,.115),.65,.45)]:
 m=unreal.load_asset(D+'/M_'+name)
 if not m:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,D,unreal.Material,unreal.MaterialFactoryNew())
 lib.delete_all_material_expressions(m)
 c=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.constant=unreal.LinearColor(*color,1);lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
 for prop,value in [(unreal.MaterialProperty.MP_METALLIC,metal),(unreal.MaterialProperty.MP_ROUGHNESS,rough)]:
  n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=value;lib.connect_material_property(n,'',prop)
 lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);materials.append(m)
for i,s in enumerate(mesh.static_materials):mesh.set_material(i,materials[1] if 'Saddle' in str(s.material_slot_name) else materials[0])
assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
b=mesh.get_bounds();size=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
assert 5<size[0]<7 and 1<size[1]<3 and 6<size[2]<7,size
(P/'import_report.json').write_text(json.dumps({'asset':mesh.get_path_name(),'size_cm':size,'center_cm':[b.origin.x,b.origin.y,b.origin.z],'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]},indent=2))
unreal.log('PRISM_IMPORT_PASS')
