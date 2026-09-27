"""Import/save three new grip models, PBR materials, and catalog icons."""
from pathlib import Path
import json,hashlib
import unreal as u

P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/GripSeriesV20'
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else dict(saved={},sources={},gameplay_tested=False)
rows=json.loads((P/'authoring.json').read_text(encoding='utf8'))['assets']
icons={ICONS+'/bow_dark_grip_'+row['id'] for row in rows}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_name().startswith(DEST+'/') or p.get_name() in icons]
if dirty:raise RuntimeError('Preserve unsaved packages '+str(dirty))

def fresh(name,folder):
    if name not in r['saved'] and E.does_asset_exist(folder+'/'+name):
        raise RuntimeError('Existing unowned asset '+folder+'/'+name)

def save(asset,source=None):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')

def texture(name,source,kind,folder):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    fresh(name,folder)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Texture import failed '+name)
    asset.srgb=kind in ('BaseColor','Icon')
    asset.compression_settings={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,
        'ORM':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,
        'Icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
    if kind=='Normal':asset.set_editor_property('flip_green_channel',True)
    if kind=='Icon':
        asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI
        asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    else:asset.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    save(asset,source);return asset

def node(mat,cls,**kwargs):
    n=L.create_material_expression(mat,cls)
    for k,v in kwargs.items():n.set_editor_property(k,v)
    return n

def wire(a,b,pin='',channel=''):
    if not L.connect_material_expressions(a,channel,b,pin):raise RuntimeError('Material connection failed '+pin)

def output(n,prop,channel=''):
    if not L.connect_material_property(n,channel,prop):raise RuntimeError('Material output failed')

def material(row,tex):
    name=row['material']
    if name in r['saved']:return u.load_asset(r['saved'][name])
    fresh(name,DEST);m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    sampled={}
    for kind,t in tex.items():
        sampler={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
            'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[kind]
        sampled[kind]=node(m,u.MaterialExpressionTextureSample,texture=t,sampler_type=sampler)
    output(sampled['BaseColor'],u.MaterialProperty.MP_BASE_COLOR,'RGB')
    output(sampled['ORM'],u.MaterialProperty.MP_ROUGHNESS,'G')
    output(sampled['ORM'],u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R')
    output(node(m,u.MaterialExpressionConstant,r=0),u.MaterialProperty.MP_METALLIC)
    normal=node(m,u.MaterialExpressionMultiply)
    wire(sampled['Normal'],normal,'A','RGB')
    wire(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.7,.7,1,1)),normal,'B')
    norm=node(m,u.MaterialExpressionNormalize);wire(normal,norm,'VectorInput')
    output(norm,u.MaterialProperty.MP_NORMAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation failed '+str(errors))
    save(m);return m

thread_name='M_Bow_Grip_Stitch'
if thread_name in r['saved']:thread=u.load_asset(r['saved'][thread_name])
else:
    fresh(thread_name,DEST);thread=A.create_asset(thread_name,DEST,u.Material,u.MaterialFactoryNew())
    output(node(thread,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.23,.155,.085,1)),u.MaterialProperty.MP_BASE_COLOR)
    output(node(thread,u.MaterialExpressionConstant,r=.86),u.MaterialProperty.MP_ROUGHNESS)
    output(node(thread,u.MaterialExpressionConstant,r=0),u.MaterialProperty.MP_METALLIC)
    errors=L.recompile_material(thread)
    if errors:raise RuntimeError('Thread material compilation failed '+str(errors))
    save(thread)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
    tex={}
    for kind in ('BaseColor','ORM','Normal'):
        name='T_Bow_Grip_'+row['name']+'_'+kind
        tex[kind]=texture(name,P/'Textures'/(name+'.png'),kind,DEST+'/Textures')
    mat=material(row,tex);name=row['mesh']
    if name not in r['saved']:
        fresh(name,DEST)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        opt.static_mesh_import_data.combine_meshes=True
        opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.build_nanite=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'))
        task.destination_path=DEST;task.destination_name=name;task.automated=True
        task.replace_existing=False;task.save=False;task.options=opt
        A.import_asset_tasks([task]);asset=u.load_asset(DEST+'/'+name)
        if not asset:raise RuntimeError('Grip mesh import failed '+name)
        slots=list(asset.static_materials)
        for slot in slots:
            slot.material_interface=thread if str(slot.material_slot_name)==thread_name else mat
        asset.static_materials=slots
        save(asset,P/'Export'/(name+'.fbx'))
    icon='bow_dark_grip_'+row['id']
    texture(icon,P/'Icons'/(icon+'.png'),'Icon',ICONS)
print('BOW_GRIP_SERIES_SAVED',json.dumps(r))
