"""A single native cubemap sample; no finite photograph or colour-border branch."""
from pathlib import Path
import hashlib,json
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreetCube20261009'
MATERIAL=BASE+'/Materials/M_Reception_IndustrialNightCube'
TEXTURE=BASE+'/Textures/T_Reception_IndustrialNightCube'
L=u.MaterialEditingLibrary
DIRECTION=r'''
float3 d=normalize(P-Eye);
float3 origin=float3(-2450.0,0.0,165.0);
// Ground-anchored box projection, expressed in the room instance's centimetres.
// Near doorway walls are true meshes; buildings/sky belong to the baked cube.
float3 bmin=float3(-18450.0,-10000.0,0.0);
float3 bmax=float3(-1650.0,10000.0,5000.0);
float3 signD=lerp(-1.0,1.0,step(0.0,d));
float3 safeD=signD*max(abs(d),0.00001);
float3 farT=(lerp(bmin,bmax,step(0.0,d))-Eye)/safeD;
float t=min(farT.x,min(farT.y,farT.z));
float3 v=(t>0.0)?(Eye+d*t-origin):d;
// The six rendered DDS faces use X=screen-right, Y=up, Z=street-forward.
return normalize(float3(-v.y,v.z,-v.x));
'''

def install(imp):
    source=json.loads((ROOT/'cube.json').read_text('utf8'))
    key=source['sha256']+':native-cube-bc7-srgb-v1'
    tex=imp.reuse(TEXTURE,key)
    if not tex:
        task=u.AssetImportTask();task.filename=source['file'];task.destination_path=BASE+'/Textures';task.destination_name=TEXTURE.rsplit('/',1)[1]
        task.factory=u.TextureFactory();task.automated=True;task.replace_existing=False;task.save=False
        imp.A.import_asset_tasks([task]);tex=imp.asset(TEXTURE)
        if not isinstance(tex,u.TextureCube):raise RuntimeError('DDS must import as a native six-face TextureCube')
        for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_BC7,
            lod_group=u.TextureGroup.TEXTUREGROUP_SKYBOX,max_texture_size=2048,
            mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():tex.set_editor_property(k,v)
        imp.saved(tex,key)
    key=hashlib.sha256((DIRECTION+':native-cube-substrate-luminance1.0').encode()).hexdigest()
    previous=imp.reuse(MATERIAL,key)
    if previous:return previous
    m=imp.A.create_asset(MATERIAL.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True);m.set_editor_property('two_sided',True)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    def node(kind,**props):
        n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin='',out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cube material connection failed: '+pin)
    def local(src):
        n=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
        wire(src,n);return n
    pos=local(node('WorldPosition'));eye=local(node('CameraPositionWS'))
    direction=node('Custom',code=DIRECTION,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,desc='Ground-anchored cubemap parallax in room instance space')
    pins=[]
    for name in ('P','Eye'):
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    direction.set_editor_property('inputs',pins);wire(pos,direction,'P');wire(eye,direction,'Eye')
    sample=node('TextureSampleParameterCube',parameter_name='IndustrialNightCube',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    wire(direction,sample,'UVs')
    scale=node('ScalarParameter',parameter_name='NightLuminance',default_value=1.)
    emission=node('Multiply');wire(sample,emission,'A','RGB');wire(scale,emission,'B')
    slab=node('SubstrateUnlitBSDF');wire(emission,slab,'EmissiveColor')
    wire(node('Constant3Vector',constant=u.LinearColor(0,0,0,1)),slab,'TransmittanceColor')
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.layout_material_expressions(m);errors=L.recompile_material(m)
    if errors:raise RuntimeError('Cubemap material build failed: '+str(errors))
    return imp.saved(m,key)
