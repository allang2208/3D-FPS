"""Selected V3 PBR, vertex tailoring finish, and existing robe visibility contract."""
import hashlib,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside V3 scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def node(m,kind,**props):
    n=L.create_material_expression(m,kind)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(n,prop,pin=''):
    if not L.connect_material_property(n,pin,prop):raise RuntimeError('Cannot connect material output')
def material(name,family=None,color=None,rough=.7,metal=0):
    m=u.load_asset(DEST+'/Materials/M_'+name) or A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    vc=node(m,u.MaterialExpressionVertexColor)
    if family:
        for channel in ('BaseColor','Normal','ORM'):
            tex=u.load_asset(DEST+'/Textures/T_'+family+'_'+channel)
            n=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name=channel,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if channel=='BaseColor':
                mul=node(m,u.MaterialExpressionMultiply);wire(n,mul,'A','RGB');wire(vc,mul,'B');output(mul,u.MaterialProperty.MP_BASE_COLOR)
            elif channel=='Normal':output(n,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                mul=node(m,u.MaterialExpressionMultiply);wire(n,mul,'A','G');wire(vc,mul,'B','A');output(mul,u.MaterialProperty.MP_ROUGHNESS)
                output(n,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R');output(n,u.MaterialProperty.MP_METALLIC,'B')
    else:
        c=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1))
        if name=='WaxedThread':
            mul=node(m,u.MaterialExpressionMultiply);wire(c,mul,'A');wire(vc,mul,'B');c=mul
        output(c,u.MaterialProperty.MP_BASE_COLOR)
        output(node(m,u.MaterialExpressionConstant,r=rough),u.MaterialProperty.MP_ROUGHNESS)
        output(node(m,u.MaterialExpressionConstant,r=metal),u.MaterialProperty.MP_METALLIC)
    output(node(m,u.MaterialExpressionConstant,r=.25),u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation '+str(errors))
    save(m);return m
def create():
    path=R/'materials.json';sha=hashlib.sha256(Path(__file__).read_bytes()+(SOURCE/'surfaces.json').read_bytes()).hexdigest()
    if path.exists():
        old=read(path)
        if old.get('revision')==sha and old.get('completed'):return old
    textures=[]
    for family in ('WalnutLeather','ReinforcedLeather','OliveTwill'):
        for channel in ('BaseColor','Normal','ORM'):
            t=u.AssetImportTask();t.filename=str(SOURCE/'Textures'/(family+'_'+channel+'.png'));t.destination_path=DEST+'/Textures';t.destination_name='T_'+family+'_'+channel;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
            if not tex:raise RuntimeError('Texture import '+t.filename)
            for key,value in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP).items():tex.set_editor_property(key,value)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR if channel=='ORM' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
            tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
            if channel=='Normal':tex.set_editor_property('normalize_normals',True)
            save(tex);textures.append(tex.get_path_name())
    mats=[material('WalnutLeather','WalnutLeather'),material('ReinforcedLeather','ReinforcedLeather'),material('OliveTwill','OliveTwill'),material('DarkLining',color=(.018,.016,.012),rough=.9),material('WaxedThread',color=read(SOURCE/'surfaces.json')['thread_linear_color'],rough=.84),material('AgedSteel',color=(.17,.18,.19),rough=.46,metal=1)]
    sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import hem_materials
    hem_materials.DEST=DEST+'/RobeMaterials'
    robe=[hem_materials.make(m).get_path_name() for m in mats]
    result=dict(completed=True,revision=sha,materials=[m.get_path_name() for m in mats],robe_materials=robe,textures=textures,normal_flip_green=True,streaming=True,runtime_tested=False)
    write(path,result);print('RANGER_V3_SURFACES_SAVED',flush=True);return result
