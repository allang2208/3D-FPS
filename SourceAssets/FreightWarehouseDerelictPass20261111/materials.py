"""Scoped patina layers and native prop instances; never replace concrete bindings."""
from pathlib import Path
import json,types
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightWarehouseDerelictPass20261111'
REVISION='freight_derelict_pass_20261111';OWNER='FreightDerelict.Owner'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
helper=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
helper=helper.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','').replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}").replace('FacilitySurface.Owner',OWNER)
scope=dict(ROOT=ROOT,BASE=BASE,REVISION=REVISION,canonical=lambda p:p.split('.')[0]);exec(compile(helper,'derelict_material_helpers','exec'),scope)
H=types.SimpleNamespace(**scope)
def build():
    m=H.own('Materials/M_SurfacePatina');L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    uv=H.node(m,'TextureCoordinate',coordinate_index=0)
    orient=H.custom(m,'return lerp(UV,float2(UV.y,1.-UV.x),saturate(Vertical));',{'UV':uv,'Vertical':H.scalar(m,'Vertical',0.)},2)
    texture=H.node(m,'TextureSampleParameter2D',parameter_name='MaskTexture',texture=u.load_asset('/Game/HospitalCorridor/Textures/Decals/T_DecalDirt_04_A'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    H.wire(orient,texture,'UVs')
    noise_asset=u.load_asset('/Game/UndergroundTunnel/Textures/Effects/T_Noise01a')
    noise=H.node(m,'TextureObjectParameter',parameter_name='VariationNoise',texture=noise_asset,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if noise_asset.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    response=H.custom(m,'''float macro=Texture2DSample(Noise,NoiseSampler,UV*float2(2.1,3.7)+Offset.xy).r;
float micro=Texture2DSample(Noise,NoiseSampler,UV*float2(17.3,21.1)+Offset.yx).r;
float edge=smoothstep(0.,.06,UV.x)*smoothstep(0.,.06,UV.y)*(1.-smoothstep(.94,1.,UV.x))*(1.-smoothstep(.94,1.,UV.y));
float a=saturate(MaskAlpha*Density*edge*lerp(.78,1.,macro));
float r=lerp(RoughMin,RoughMax,saturate(macro*.65+micro*.35));
return float3(a,r,lerp(.87,1.04,macro));''',
        {'UV':orient,'Noise':noise,'MaskAlpha':(texture,'A'),'Density':H.scalar(m,'Density',.3),
         'RoughMin':H.scalar(m,'RoughMin',.8),'RoughMax':H.scalar(m,'RoughMax',.98),
         'Offset':H.node(m,'VectorParameter',parameter_name='Offset',default_value=u.LinearColor(.13,.47,0,0))},3)
    def channel(r,g,b):
        n=H.node(m,'ComponentMask',r=r,g=g,b=b,a=False);H.wire(response,n);return n
    H.output(channel(True,False,False),'OPACITY');H.output(channel(False,True,False),'ROUGHNESS')
    col=H.node(m,'Multiply');H.wire(texture,col,'A','RGB');H.wire(channel(False,False,True),col,'B')
    tinted=H.node(m,'Multiply');H.wire(col,tinted,'A');H.wire(H.node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.8,.8,.8,1)),tinted,'B')
    H.output(tinted,'BASE_COLOR');H.save(m)
    masks='/Game/HospitalCorridor/Textures/Decals/'
    configs=[('Dust',masks+'T_DecalDirt_04_A',.34,.84,.98,(.83,.82,.77),0),
             ('Scuff',masks+'T_DecalDirt_03_A',.38,.53,.78,(.59,.60,.59),0),
             ('Damp',masks+'T_DecalDirt_02_A',.20,.58,.87,(.23,.25,.24),0),
             ('Oil',masks+'T_FloorStain_01_A',.28,.30,.56,(.12,.13,.12),0),
             ('Leak','/Game/Dungeons/FacilityQuixel20261108/Leakage/Textures/T_Leakage_BaseOpacity',.21,.58,.9,(.7,.73,.68),1)]
    result={}
    for name,tex,density,rmin,rmax,tint,vertical in configs:
        mi=H.instance(name,m,{'Density':density,'RoughMin':rmin,'RoughMax':rmax,'Vertical':vertical},{'Tint':tint})
        L.set_material_instance_texture_parameter_value(mi,'MaskTexture',u.load_asset(tex));H.save(mi);result[name]=mi.get_path_name()
    mi=H.own('Materials/MI_LocalConcreteLoss',u.MaterialInstanceConstant,'/Game/Dungeons/FacilityQuixel20261108/DamagedConcrete/Materials/MI_DamagedConcrete')
    L.set_material_instance_scalar_parameter_value(mi,'OpacityStrength',.87)
    result['Damage']=H.save(mi).get_path_name()
    return result
PROP_CACHE={}
def prop_variant(source,state):
    key=(source.get_path_name(),state)
    if key in PROP_CACHE:return PROP_CACHE[key]
    if source.get_base_material().get_path_name()!='/Game/UndergroundTunnel/Materials/Master/M_Env_Basic.M_Env_Basic':return source
    native=source.get_path_name()
    mi=H.own('Materials/'+source.get_name()+'_'+state,u.MaterialInstanceConstant,native)
    # Native dust uses a slope mask. Retain every original PBR map and its normal
    # blending, changing only dust response and moderate wood detail strength.
    L.set_material_instance_scalar_parameter_value(mi,'Dust Blend',.22 if state=='Handled' else .42)
    L.set_material_instance_vector_parameter_value(mi,'Dust Colour',u.LinearColor(.34,.32,.27,1))
    L.set_material_instance_scalar_parameter_value(mi,'Dust Roughness',.94)
    L.set_material_instance_scalar_parameter_value(mi,'Slope',.78)
    if 'Wood' in source.get_name():
        L.set_material_instance_scalar_parameter_value(mi,'Detail Normal Intensity',.55)
    H.save(mi);PROP_CACHE[key]=mi;return mi
