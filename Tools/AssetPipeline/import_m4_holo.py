import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Holographic20260909')
dest='/Game/Weapons/M4Holographic'
unreal.EditorAssetLibrary.make_directory(dest)
t=unreal.AssetImportTask();t.filename=str(out/'SM_M4_Holographic.fbx');t.destination_path=dest;t.destination_name='SM_M4_Holographic';t.automated=True;t.replace_existing=True;t.save=True
o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;o.import_as_skeletal=False;o.import_materials=False;o.import_textures=False
o.static_mesh_import_data.combine_meshes=True;t.options=o
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
mesh=unreal.load_asset(dest+'/SM_M4_Holographic');assert isinstance(mesh,unreal.StaticMesh)
lib=unreal.MaterialEditingLibrary
def material(name):
 m=unreal.load_asset(dest+'/'+name)
 if not m:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,dest,unreal.Material,unreal.MaterialFactoryNew())
 lib.delete_all_material_expressions(m);return m
def tex(m,path):
 n=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample);n.texture=unreal.load_asset(path);assert n.texture;return n
m=material('M_HoloBody');base=tex(m,'/Game/Holographic_low_Holosight_BaseColor');lib.connect_material_property(base,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);lib.connect_material_property(base,'A',unreal.MaterialProperty.MP_OPACITY_MASK)
packed_path=dest+'/T_HoloORM'
packed=unreal.load_asset(packed_path) if unreal.EditorAssetLibrary.does_asset_exist(packed_path) else unreal.EditorAssetLibrary.duplicate_asset('/Game/Holographic_low_Holosight_OcclusionRoughnessMetallic',packed_path)
packed.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS);packed.set_editor_property('srgb',False);unreal.EditorAssetLibrary.save_loaded_asset(packed)
orm=tex(m,packed_path);orm.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
for channel,prop in [('R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',unreal.MaterialProperty.MP_ROUGHNESS),('B',unreal.MaterialProperty.MP_METALLIC)]:lib.connect_material_property(orm,channel,prop)
lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
r=material('M_HoloReticle');r.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);r.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);r.set_editor_property('two_sided',True)
dot=tex(r,'/Game/Holographic_low_Red_Dot_Emissive');lib.connect_material_property(dot,'R',unreal.MaterialProperty.MP_OPACITY_MASK)
bright=lib.create_material_expression(r,unreal.MaterialExpressionMultiply);bright.set_editor_property('const_b',50.0);lib.connect_material_expressions(dot,'RGB',bright,'A');lib.connect_material_property(bright,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.recompile_material(r);unreal.EditorAssetLibrary.save_loaded_asset(r)
for i,s in enumerate(mesh.static_materials):mesh.set_material(i,r if 'Red' in str(s.material_slot_name) else m)
unreal.EditorAssetLibrary.save_loaded_asset(mesh)
b=mesh.get_bounding_box();(out/'ue-import.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),bounds=[str(b.min),str(b.max)],slots=[str(s.material_slot_name) for s in mesh.static_materials]),indent=2))
unreal.log('M4_HOLO_IMPORT_PASS')
