"""Import and save new food packages in the isolated commandlet host."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/CampfireUpgrade20261026'
if Path(u.Paths.project_dir()).resolve()!=(OUT/'AssetHost').resolve():raise RuntimeError('Isolated asset host required')
ROWS=json.loads((OUT/'foods.json').read_text(encoding='utf-8'))
BASE='/Game/Items/Consumables/WildGame20261026';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
E.make_directory(BASE);saved=[]
def import_asset(file,name,options=None):
    t=u.AssetImportTask()
    for k,v in [('filename',str(file)),('destination_path',BASE),('destination_name',name),('automated',True),('replace_existing',True),('save',True)]:t.set_editor_property(k,v)
    if options:t.set_editor_property('options',options)
    A.import_asset_tasks([t]);asset=E.load_asset(BASE+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    saved.append(asset.get_path_name())
for row in ROWS:
  for state in ('Raw','Roasted'):
    textures={}
    for suffix in ('BaseColor','Roughness','NormalGL'):
        n=f'T_{state}{row["key"]}_{suffix}';t=import_asset(OUT/'Maps'/f'{n}.png',n)
        t.set_editor_property('srgb',suffix=='BaseColor')
        if suffix=='NormalGL':
            t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
        elif suffix=='Roughness':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
        t.set_editor_property('max_texture_size',1024);save(t);textures[suffix]=t
    name=f'M_{state}{row["key"]}';m=E.load_asset(BASE+'/'+name) if E.does_asset_exist(BASE+'/'+name) else A.create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    for suffix,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('NormalGL',u.MaterialProperty.MP_NORMAL)]:
        n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[suffix])
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        if not L.connect_material_property(n,'R' if suffix=='Roughness' else 'RGB',prop):raise RuntimeError('Material connection failed')
    for value,prop in [(0.,u.MaterialProperty.MP_METALLIC),(.28,u.MaterialProperty.MP_SPECULAR)]:
        c=L.create_material_expression(m,u.MaterialExpressionConstant);c.set_editor_property('r',value);L.connect_material_property(c,'',prop)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);L.recompile_material(m);save(m)
    name=f'SM_{state}{row["key"]}';opts=u.FbxImportUI()
    for k,v in [('import_as_skeletal',False),('import_materials',False),('import_textures',False),('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)]:opts.set_editor_property(k,v)
    data=opts.get_editor_property('static_mesh_import_data');data.set_editor_property('auto_generate_collision',True);data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    mesh=import_asset(OUT/'Export'/f'{name}.fbx',name,opts);mesh.set_material(0,m);save(mesh)
(OUT/'ue-authoring.json').write_text(json.dumps({'saved_assets':saved,'host':u.Paths.project_dir(),'gameplay_test':False},indent=2),encoding='utf-8')
print('CAMPFIRE_FOOD_ASSETS_SAVED',len(saved))
