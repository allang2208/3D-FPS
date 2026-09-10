import unreal,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909');DEST='/Game/Weapons/M4Drum'
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
o.import_as_skeletal=False;o.import_materials=False;o.import_textures=False;o.static_mesh_import_data.combine_meshes=True
t=unreal.AssetImportTask();t.filename=str(OUT/'SM_M4_LargeDrum.fbx');t.destination_path=DEST;t.destination_name='SM_M4_LargeDrum';t.automated=True;t.replace_existing=True;t.save=True;t.options=o
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);assert t.imported_object_paths
mesh=unreal.load_asset(DEST+'/SM_M4_LargeDrum');assert mesh
lib=unreal.MaterialEditingLibrary
def material(name):
 m=unreal.load_asset(DEST+'/'+name)
 if not m:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
 lib.delete_all_material_expressions(m);return m
poly=material('M_M4DrumPolymer')
rough=unreal.load_asset(DEST+'/T_M4Drum_Roughness')
if not rough:rough=unreal.EditorAssetLibrary.duplicate_asset('/Game/Magazine_Light_Roughness',DEST+'/T_M4Drum_Roughness')
assert rough
rough.set_editor_property('srgb',False)
assert unreal.EditorAssetLibrary.save_loaded_asset(rough,only_if_is_dirty=False)
for channel,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
 n=lib.create_material_expression(poly,unreal.MaterialExpressionTextureSample);n.texture=rough if channel=='Roughness' else unreal.load_asset('/Game/Magazine_Light_BaseColor');assert n.texture
 if channel!='BaseColor':n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 # Reuse the rifle's colour and wear texture with a nonmetal polymer finish.
 mul=lib.create_material_expression(poly,unreal.MaterialExpressionMultiply);mul.set_editor_property('const_b',.7 if channel=='BaseColor' else .25)
 lib.connect_material_expressions(n,'RGB' if channel=='BaseColor' else 'R',mul,'A')
 if channel=='Roughness':
  add=lib.create_material_expression(poly,unreal.MaterialExpressionAdd);add.set_editor_property('const_b',.55);lib.connect_material_expressions(mul,'',add,'A');mul=add
 lib.connect_material_property(mul,'',prop)
def constant(m,value,prop):
 n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.set_editor_property('r',value);lib.connect_material_property(n,'',prop)
constant(poly,0,unreal.MaterialProperty.MP_METALLIC)
steel=material('M_M4DrumFasteners');n=lib.create_material_expression(steel,unreal.MaterialExpressionTextureSample);n.texture=unreal.load_asset('/Game/Body_BaseColor');lib.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_BASE_COLOR);constant(steel,.7,unreal.MaterialProperty.MP_METALLIC);constant(steel,.44,unreal.MaterialProperty.MP_ROUGHNESS)
index=material('M_M4DrumIndex');n=lib.create_material_expression(index,unreal.MaterialExpressionConstant3Vector);n.set_editor_property('constant',unreal.LinearColor(.34,.21,.07,1));lib.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR);constant(index,.7,unreal.MaterialProperty.MP_ROUGHNESS)
for m in [poly,steel,index]:lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
for i,s in enumerate(mesh.static_materials):mesh.set_material(i,steel if 'Fastener' in str(s.material_slot_name) else index if 'Index' in str(s.material_slot_name) else poly)
assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
(OUT/'import.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),materials=[str(s.material_slot_name) for s in mesh.static_materials]),indent=2))
unreal.log('M4_DRUM_IMPORT_PASS')
