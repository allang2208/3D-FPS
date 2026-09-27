"""Import/save only this batch's materials, fitted meshes and catalog textures."""
from pathlib import Path
import json,hashlib
import unreal as u
P=Path(__file__).parent
series=json.loads((P/'series.json').read_text(encoding='utf8'));DEST=series['asset_directory']
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: end play before saving this batch')
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf8')) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
icons={ICONS+'/bow_dark_arrow_rest_'+row['id'] for row in series['variants']}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_name().startswith(DEST+'/') or p.get_name() in icons]
if dirty:raise RuntimeError('Preserve unsaved target packages '+str(dirty))

def existing(name,folder):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Unowned target asset '+folder+'/'+name)
    return None
def save(asset,source=None):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8');print('BOW_REST_SAVED',asset.get_path_name(),flush=True)
def texture(name,kind,folder):
    asset=existing(name,folder)
    if asset:return asset
    source=P/('Icons' if kind=='Icon' else 'Textures')/(name+'.png')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Texture import failed '+name)
    asset.srgb=kind in ('BaseColor','Icon')
    asset.compression_settings={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'ORM':u.TextureCompressionSettings.TC_MASKS,
        'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'Icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
    if kind=='Normal':asset.set_editor_property('flip_green_channel',True)
    if kind=='Icon':
        asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI;asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    else:asset.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    save(asset,source);return asset
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def output(n,prop,channel=''):
    if not L.connect_material_property(n,channel,prop):raise RuntimeError('Material output failed '+str(prop))
materials={}
source=json.loads((P/'source-binding.json').read_text(encoding='utf8'))
materials['ArrowRestWood']=u.load_asset(source['materials']['ArrowRestWood'])
if not materials['ArrowRestWood']:raise RuntimeError('Current carved wood material missing')
for label in ['Horn','Leather']:
    name='M_BowRest_'+label;m=existing(name,DEST)
    if not m:
        tex={kind:texture('T_BowRest_'+label+'_'+kind,kind,DEST+'/Textures') for kind in ['BaseColor','ORM','Normal']}
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());samples={}
        for kind,t in tex.items():
            samples[kind]=node(m,u.MaterialExpressionTextureSample,texture=t,
                sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                              'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[kind])
        output(samples['BaseColor'],u.MaterialProperty.MP_BASE_COLOR,'RGB')
        output(samples['ORM'],u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R')
        output(samples['ORM'],u.MaterialProperty.MP_ROUGHNESS,'G')
        output(samples['Normal'],u.MaterialProperty.MP_NORMAL,'RGB')
        output(node(m,u.MaterialExpressionConstant,r=0),u.MaterialProperty.MP_METALLIC)
        output(node(m,u.MaterialExpressionConstant,r=.35),u.MaterialProperty.MP_SPECULAR)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Material compile failed '+str(errors))
        save(m)
    materials[name]=m
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for row in series['variants']:
        name=row['mesh'];mesh=existing(name,DEST)
        if not mesh:
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
            d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.build_nanite=False
            d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            source=P/'Export'/(name+'.fbx');task=u.AssetImportTask();task.filename=str(source)
            task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False;task.options=opt
            A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
            if not mesh:raise RuntimeError('Arrow rest import failed '+name)
            slots=list(mesh.static_materials)
            for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
            mesh.static_materials=slots;save(mesh,source)
        texture('bow_dark_arrow_rest_'+row['id'],'Icon',ICONS)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('BOW_REST_ASSETS_COMPLETE',len(r['saved']))
