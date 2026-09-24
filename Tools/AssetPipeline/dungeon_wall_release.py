"""Approved wall-material release for the dungeon's existing material identities.

Authoring-time only. No level loading, runtime work, geometry or collision edits.
"""
import hashlib,json
from pathlib import Path
import unreal as u
PROJECT=Path(__file__).resolve().parents[2]
ROOT=PROJECT/'SourceAssets/DungeonWallUpgrade20260924'
CONFIG=ROOT/'Config/production-release.json'
BASE='/Game/Dungeons/WallUpgrade20260924'
CONCRETE='/Game/Dungeons/AtmosphereV2/Materials/M_Concrete'
TAG='DungeonWallPublished20260924'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary

def enabled():
    return CONFIG.exists() and json.loads(CONFIG.read_text(encoding='utf-8')).get('enabled',False)

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Wall release save failed '+asset.get_path_name())

def apply_instance(mi,save_asset=True):
    if not enabled():return False
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    target=cfg['instance_aliases'].get(mi.get_path_name().split('.')[0])
    if not target:return False
    parent=u.load_asset(target)
    if not parent:raise RuntimeError('Install approved wall candidate first: '+target)
    # The release instance owns all look parameters. Historical overrides must not
    # shadow identically named parameters such as NormalStrength or Brightness.
    if mi.get_editor_property('parent')==parent and not any(mi.get_editor_property(k) for k in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']):return True
    mi.modify();L.clear_all_material_instance_parameters(mi)
    L.set_material_instance_parent(mi,parent);L.update_material_instance(mi)
    E.set_metadata_tag(mi,TAG,target)
    if save_asset:save(mi)
    return True

def apply_existing_aliases():
    if not enabled():return
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    for path in cfg['instance_aliases']:
        if E.does_asset_exist(path):apply_instance(u.load_asset(path))

def publish_concrete():
    """Append the approved graph and reconnect outputs; do not delete a live graph."""
    if not enabled():return False
    mat=u.load_asset(CONCRETE);approved=u.load_asset(BASE+'/Materials/MI_WallConcrete')
    if not mat or not approved:raise RuntimeError('Missing concrete or approved wall material')
    source=approved.get_base_material()
    custom_nodes=[n for n in L.get_material_expressions(source) if isinstance(n,u.MaterialExpressionCustom)]
    if len(custom_nodes)!=1:raise RuntimeError('Approved graph layout changed; preserve production')
    code=custom_nodes[0].get_editor_property('code')
    expected=[str(p.get_editor_property('input_name')) for p in custom_nodes[0].get_editor_property('inputs')]
    scalars={key:float(L.get_material_instance_scalar_parameter_value(approved,key)) for key in ['TileCm','DepthCm','NormalStrength','GrainTileCm','GrainStrength','Brightness','RoughnessScale']}
    texture_names=['ColorTex','NormalTex','SurfaceTex','HeightTex','GrainNormal','GrainSurface']
    textures={key:L.get_material_instance_texture_parameter_value(approved,key) for key in texture_names}
    if not all(textures.values()):raise RuntimeError('Approved texture parameter missing')
    tint=L.get_material_instance_vector_parameter_value(approved,'Tint')
    signature=hashlib.sha256(json.dumps({'code':code,'scalars':scalars,'textures':{k:v.get_path_name() for k,v in textures.items()},'tint':[tint.r,tint.g,tint.b,tint.a]},sort_keys=True).encode()).hexdigest()
    prior=E.get_metadata_tag(mat,TAG)
    if prior:
        if prior!=signature:raise RuntimeError('Approved appearance changed after release; create an explicit revision')
        return True
    mat.modify();mat.set_editor_property('tangent_space_normal',False)
    mat.set_editor_property('used_with_instanced_static_meshes',True);mat.set_editor_property('used_with_nanite',True)
    def node(kind,**props):
        n=L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin='',output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Wall connection '+pin)
    world=node('WorldPosition');pos=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE);wire(world,pos)
    def local(src):
        dst=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE);wire(src,dst);return dst
    dist=node('Distance');wire(world,dist,'A');wire(node('CameraPositionWS'),dist,'B')
    inputs={'Position':pos,'SurfaceNormal':local(node('VertexNormalWS')),'ViewLocal':local(node('CameraVectorWS')),'DistanceCm':dist}
    for key,value in scalars.items():inputs[key]=node('ScalarParameter',parameter_name=key,default_value=value)
    inputs['Tint']=node('VectorParameter',parameter_name='Tint',default_value=tint)
    for key,tex in textures.items():
        sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key in ['NormalTex','GrainNormal'] else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='ColorTex' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if key=='HeightTex' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        inputs[key]=node('TextureObjectParameter',parameter_name=key,texture=tex,sampler_type=sampler)
    inputs['OriginalUV']=node('TextureCoordinate')
    for pin,suffix,sampler in [('OriginalColor','BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('OriginalNormal','Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('OriginalRoughness','Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        inputs[pin]=node('TextureObject',texture=u.load_asset('/Game/Dungeons/AtmosphereV2/Textures/T_Concrete_'+suffix),sampler_type=sampler)
    if set(expected)!=set(inputs):raise RuntimeError('Approved material inputs changed')
    custom=node('Custom',code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,desc='Published scanned wall, approved instance parameters; horizontal concrete retained')
    pins=[]
    for key in expected:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    custom.set_editor_property('inputs',pins);outputs=[]
    for key,kind in [('NormalLocal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Specular',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        o=u.CustomOutput();o.set_editor_property('output_name',key);o.set_editor_property('output_type',kind);outputs.append(o)
    custom.set_editor_property('additional_outputs',outputs)
    for key,src in inputs.items():wire(src,custom,key)
    col=node('ComponentMask',r=True,g=True,b=True,a=False);wire(custom,col)
    rough=node('ComponentMask',r=False,g=False,b=False,a=True);wire(custom,rough)
    normal=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire(custom,normal,output='NormalLocal')
    for src,pin,prop in [(col,'','BASE_COLOR'),(rough,'','ROUGHNESS'),(normal,'','NORMAL'),(custom,'AO','AMBIENT_OCCLUSION'),(custom,'Specular','SPECULAR'),(node('Constant',r=0.),'','METALLIC')]:
        if not L.connect_material_property(src,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Wall output '+prop)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    # Required build, not a scene test. Statistics waits for the shader resource.
    stats=L.get_statistics(mat)
    E.set_metadata_tag(mat,TAG,signature);L.layout_material_expressions(mat);save(mat)
    print('PUBLISHED_WALL_CONCRETE',signature,'instructions',stats.get_editor_property('num_pixel_shader_instructions'),flush=True)
    return True
