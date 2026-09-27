"""Import and persist this batch only; no PIE or runtime validation."""
from pathlib import Path
import json,hashlib,importlib.util
import unreal as u
P=Path(__file__).parent
reticle_spec=importlib.util.spec_from_file_location('bow_reticle_author',P/'ReticleReadability/materials.py')
reticle_author=importlib.util.module_from_spec(reticle_spec);reticle_spec.loader.exec_module(reticle_author)
series=json.loads((P/'series.json').read_text(encoding='utf8'));DEST=series['asset_directory']
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: end play before saving this batch')
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf8')) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
icons={ICONS+'/bow_dark_sight_'+row['id'] for row in series['variants']}
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
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8');print('BOW_OPTIC_SAVED',asset.get_path_name(),flush=True)
def texture(name,kind,folder):
    asset=existing(name,folder)
    if asset:return asset
    source=P/('Icons' if kind=='Icon' else 'Textures')/(name+'.png')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Texture import failed '+name)
    asset.srgb=kind=='Icon'
    asset.compression_settings={'ORM':u.TextureCompressionSettings.TC_MASKS,
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
def wire(n,channel,target,pin):
    if not L.connect_material_expressions(n,channel,target,pin):raise RuntimeError('Material connection failed '+pin)
def scalar(m,v):return node(m,u.MaterialExpressionConstant,r=v)
def color(m,rgb):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1))
def compile_save(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile failed '+str(errors))
    save(m)
materials={}
for slot,name in [('BracketBowWood','M_Bow_BracketWood'),('BracketWaxedLinen','M_Bow_BracketWaxedLinen')]:
    materials[slot]=u.load_asset('/Game/Weapons/DarkBow20260925/WoodBracketV19/'+name)
    if not materials[slot]:raise RuntimeError('Retained bracket material missing '+name)
tex={kind:texture('T_BowOptic_Metal'+kind,kind,DEST+'/Textures') for kind in ['ORM','Normal']}
for label,rgb in [('BlackSteel',(.055,.064,.073)),('DarkBronze',(.23,.15,.071)),('Etching',(.009,.011,.013))]:
    name='M_BowOptic_'+label;m=existing(name,DEST)
    if not m:
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        output(color(m,rgb),u.MaterialProperty.MP_BASE_COLOR)
        if label=='Etching':
            reticle_author.hide_old_etching(m)
        else:
            orm=node(m,u.MaterialExpressionTextureSample,texture=tex['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            normal=node(m,u.MaterialExpressionTextureSample,texture=tex['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            output(orm,u.MaterialProperty.MP_METALLIC,'B');output(orm,u.MaterialProperty.MP_ROUGHNESS,'G')
            output(normal,u.MaterialProperty.MP_NORMAL,'RGB')
        compile_save(m)
    materials[name]=m
for power,rgb in [(2,(.80,.92,.95)),(4,(.88,.84,.96))]:
    name='M_BowOptic_Glass'+str(power)+'x';m=existing(name,DEST)
    if not m:
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        reticle_author.build_lens(m,power)
        compile_save(m)
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
            if not mesh:raise RuntimeError('Optic import failed '+name)
            slots=list(mesh.static_materials)
            for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
            mesh.static_materials=slots;save(mesh,source)
        texture('bow_dark_sight_'+row['id'],'Icon',ICONS)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('BOW_OPTIC_ASSETS_COMPLETE',len(r['saved']))
