"""Save the two native combat belts, materials, display meshes and UI textures."""
import ast,gc,sys,types
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from combat_belts_common import *

E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
SS=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
DEST='';KEY='';mats=[];slots=[]

def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing production source '+path)
    return asset

def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside combat belt destination')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())

def functions(path,names,namespace):
    text=(P/path).read_text(encoding='utf-8-sig');tree=ast.parse(text)
    code='\n\n'.join(ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
    code=code.replace("'TacticalBeltRevision','native-waist-v1'","'CombatBeltRevision','integration-r1'")
    exec(compile(code,str(path),'exec'),namespace)

# Reuse the existing native skeleton and render-LOD save contract without
# executing the old belt's author or publishing to any of its destinations.
io=types.SimpleNamespace();env=dict(u=u,G=G,B=B)
functions('Tools/ChainmailPants/save_assets.py',{'dynamic'},env);io.dynamic=env['dynamic']
staticio=types.SimpleNamespace();env=dict(u=u)
functions('Tools/FieldHat/save_icon.py',{'dynamic'},env);staticio.dynamic=env['dynamic']
functions('Tools/TacticalMagazineBelt/save_assets.py',{'skeletal','static'},globals())

def import_texture(filename,name,folder,channel=None,resolution=0):
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder
    task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);texture=load(folder+'/'+name)
    if channel:
        props=dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,
            flip_green_channel=channel=='Normal',never_stream=False,max_texture_size=resolution,compression_no_alpha=True,
            address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP)
    else:
        props=dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
            mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True)
    for key,value in props.items():texture.set_editor_property(key,value)
    save(texture);return texture

def material(row,textures):
    name='M_'+row['name'];folder=DEST+'/Materials';E.make_directory(folder)
    mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
    glass=row['transmission']>.01
    mat.set_editor_property('use_material_attributes',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if glass else u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT if glass else u.MaterialShadingModel.MSM_CLOTH if row['cloth'] else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def node(cls):return L.create_material_expression(mat,cls)
    attrs=node(u.MaterialExpressionMakeMaterialAttributes)
    attribute_pins={u.MaterialProperty.MP_BASE_COLOR:'BaseColor',u.MaterialProperty.MP_NORMAL:'Normal',
        u.MaterialProperty.MP_AMBIENT_OCCLUSION:'AmbientOcclusion',u.MaterialProperty.MP_ROUGHNESS:'Roughness',
        u.MaterialProperty.MP_METALLIC:'Metallic',u.MaterialProperty.MP_SPECULAR:'Specular',
        u.MaterialProperty.MP_SUBSURFACE_COLOR:'SubsurfaceColor',u.MaterialProperty.MP_EMISSIVE_COLOR:'EmissiveColor',
        u.MaterialProperty.MP_OPACITY:'Opacity'}
    def scalar(value):
        n=node(u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
    def color(value):
        n=node(u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*value,1));return n
    def output(n,prop,channel=''):
        if not L.connect_material_expressions(n,channel,attrs,attribute_pins[prop]):raise RuntimeError('Material connection '+str(prop))
    base_sample=None
    if row['family']:
        for channel in ('BaseColor','Normal','ORM'):
            n=node(u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel)
            n.set_editor_property('texture',textures[row['family']+'_'+channel])
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if channel=='BaseColor':
                base_sample=n;output(n,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif channel=='Normal':output(n,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:output(n,prop,pin)
    else:
        output(color(row['color']),u.MaterialProperty.MP_BASE_COLOR)
        output(scalar(row['roughness']),u.MaterialProperty.MP_ROUGHNESS)
        output(scalar(row['metallic']),u.MaterialProperty.MP_METALLIC)
    output(scalar(.3 if row['cloth'] else .45),u.MaterialProperty.MP_SPECULAR)
    if row['cloth']:
        if base_sample:
            tint=node(u.MaterialExpressionMultiply)
            L.connect_material_expressions(base_sample,'RGB',tint,'A')
            L.connect_material_expressions(scalar(.15),'',tint,'B')
        else:tint=color([v*.15 for v in row['color']])
        output(tint,u.MaterialProperty.MP_SUBSURFACE_COLOR)
        if not L.connect_material_expressions(scalar(.1),'',attrs,'ClearCoat'):raise RuntimeError('Cloth fuzz connection')
    if row['emission_strength']>0:
        output(color([v*row['emission_strength'] for v in row['emission']]),u.MaterialProperty.MP_EMISSIVE_COLOR)
    if glass:
        # Real-time tinted transmission; the saved source retains solid quartz.
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        thin=node(u.MaterialExpressionThinTranslucentMaterialOutput)
        tint=color([.64,.50,.80]);pin=str(L.get_material_expression_input_names(thin)[0])
        if not L.connect_material_expressions(tint,'',thin,pin):raise RuntimeError('Quartz transmission')
        output(scalar(0.),u.MaterialProperty.MP_OPACITY)
    if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Material attributes output')
    if L.recompile_material(mat):raise RuntimeError('Material compile failed '+name)
    save(mat);return mat

def produce(which):
    global DEST,KEY,mats,slots
    row=BELTS[which];src=source(row);out=R/which;DEST=destination(row);KEY=row['key']
    delivery=read(out/'delivery.json');receipt_path=out/'saved_assets.json'
    receipt=read(receipt_path) if receipt_path.exists() else dict(completed=False,wear={},runtime_tested=False,multiplayer_tested=False)
    receipt['completed']=False
    def record():write(receipt_path,receipt)
    record();textures={};material_rows=read(out/'materials.json')
    fingerprint=sha(out/'materials.json')+sha(src/'textures.json')+sha(Path(__file__))
    if receipt.get('material_fingerprint')==fingerprint:
        textures={key:load(value) for key,value in receipt['textures'].items()};mats=[load(path) for path in receipt['materials']]
    else:
        for family in read(src/'textures.json')['maps']:
            for channel in ('BaseColor','Normal','ORM'):
                name='T_'+family['name']+'_'+channel
                textures[family['name']+'_'+channel]=import_texture(src/'Textures'/(name+'.png'),name,DEST+'/Textures',channel,family['resolution'])
        mats=[material(v,textures) for v in material_rows]
        receipt.update(material_fingerprint=fingerprint,materials=[m.get_path_name() for m in mats],textures={key:v.get_path_name() for key,v in textures.items()});record()
    slots=[v['name'] for v in material_rows]
    for body in delivery['records']:
        rows=body['lods'];hashes=[sha(v['file']) for v in rows]
        if receipt['wear'].get(body['body'],{}).get('lod_source_hashes')!=hashes:
            receipt['wear'][body['body']]=skeletal(rows,body['source'],DEST+'/Wear/SK_'+row['stem']+'_'+body['body'])
            record();print('COMBAT_BELT_WEAR_SAVED',KEY,body['body'],flush=True)
        gc.collect();u.SystemLibrary.collect_garbage()
    rows=next(v['lods'] for v in delivery['records'] if v['body']=='Jason')
    if receipt.get('pickup',{}).get('lod_source_hashes')!=[sha(v['file']) for v in rows]:
        data=read(rows[0]['file']);offset=[-(min(p[i] for p in data['positions'])+max(p[i] for p in data['positions']))*.5 for i in range(3)];del data
        receipt['pickup']=static(rows,DEST+'/Pickups/SM_'+row['stem'],offset);record()
    display=out/(KEY+'-display.json')
    if receipt.get('icon',{}).get('lod_source_hashes')!=[sha(display)]:
        receipt['icon']=static([dict(file=str(display))],DEST+'/Icons/SM_'+row['stem']+'_Icon');record()
    texture=import_texture(out/(KEY+'.png'),'T_'+row['stem']+'_Icon',DEST+'/Icons')
    receipt.update(completed=True,icon_texture=texture.get_path_name(),icon_sha256=sha(out/(KEY+'.png')),source_manifest_sha256=sha(out/'delivery.json'),
        geometry_revision=delivery.get('geometry_revision'),
        fit_reference='Native Jason / Kaitlin and saved ST6 waist; other garment shapes require derived fit',new_storage_capacity=False)
    receipt.pop('pending_geometry_revision',None)
    record();print('COMBAT_BELT_ASSETS_SAVED',KEY,flush=True)

def require_asset_window():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Preserve active PIE; defer belt import')

if __name__=='__main__':
    require_asset_window()
    for which in BELTS:produce(which)
