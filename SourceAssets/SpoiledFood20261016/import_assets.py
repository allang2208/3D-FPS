"""Import and save the new spoiled-food packages in the current UE batch."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpoiledFood20261016')
DEST='/Game/Items/Consumables/SpoiledFood20261016'
prep=json.loads((ROOT/'preparation.json').read_text())
AT=u.AssetToolsHelpers.get_asset_tools();EAL=u.EditorAssetLibrary;MEL=u.MaterialEditingLibrary
saved=[]
def imp(name,file,options=None):
    path=DEST+'/'+name
    if EAL.does_asset_exist(path):raise RuntimeError('Preserve existing package: '+path)
    t=u.AssetImportTask();t.filename=str(ROOT/file);t.destination_path=DEST;t.destination_name=name
    t.automated=True;t.replace_existing=False;t.save=False
    if options:t.options=options
    AT.import_asset_tasks([t]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed: '+path)
    return asset
def save(asset):
    if not EAL.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())

textures={}
for suffix in ['BaseColor','Roughness','NormalGL']:
    name='T_SpoiledFood_'+suffix;tex=imp(name,name+'.png')
    tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('never_stream',False)
    if suffix=='NormalGL':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif suffix=='Roughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    textures[suffix]=tex;save(tex)
if EAL.does_asset_exist(DEST+'/M_SpoiledFood'):raise RuntimeError('Preserve existing material')
material=AT.create_asset('M_SpoiledFood',DEST,u.Material,u.MaterialFactoryNew())
material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
for row,(suffix,prop,sampler) in enumerate([
    ('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR),
    ('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS),
    ('NormalGL',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]):
    n=MEL.create_material_expression(material,u.MaterialExpressionTextureSample,-400,row*210)
    n.set_editor_property('texture',textures[suffix]);n.set_editor_property('sampler_type',sampler)
    if not MEL.connect_material_property(n,'R' if suffix=='Roughness' else 'RGB',prop):raise RuntimeError('Material connection failed')
for row,(value,prop) in enumerate([(0.,u.MaterialProperty.MP_METALLIC),(.27,u.MaterialProperty.MP_SPECULAR)]):
    n=MEL.create_material_expression(material,u.MaterialExpressionConstant,-200,700+100*row);n.r=value
    if not MEL.connect_material_property(n,'',prop):raise RuntimeError('Material scalar connection failed')
MEL.recompile_material(material);save(material)
opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opts.automated_import_should_detect_type=False
data=opts.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=True
data.generate_lightmap_u_vs=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
mesh=imp('SM_SpoiledFood','SM_SpoiledFood.fbx',opts);mesh.set_material(0,material)
save(mesh)
b=mesh.get_bounds()
receipt={'saved_packages':saved,'mesh':mesh.get_path_name(),'dimensions_cm':[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z],
    'material':material.get_path_name(),'texture_maps':list(textures),'normal_green_flipped':True,
    'game_or_pie_started':False,'runtime_test_performed':False}
(ROOT/'ue-assets.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print('SPOILED_FOOD_SAVED',json.dumps(receipt))
