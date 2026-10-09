"""One generated, streamed night image and a bounded procedural asphalt surface."""
from pathlib import Path
import hashlib,json
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009'
L=u.MaterialEditingLibrary

PROJECTION=r'''
float3 ray = P - Eye;
float dx = min(ray.x, -0.1);
float3 distant = Eye + ray * ((-3800.0 - Eye.x) / dx);
// UE local -Y is screen-right while looking out of the west-facing doorway.
// 19.8 x 9.9 metres preserves the generated 2:1 image aspect ratio.
return float2(0.5 - distant.y / 1980.0, 0.53 - (distant.z - 165.0) / 990.0);
'''
ASPHALT=r'''
float2 p = UV * 185.0;
float2 f = frac(p), i = floor(p); f = f*f*(3.0-2.0*f);
float4 h = frac(sin(float4(dot(i,float2(127.1,311.7)),
 dot(i+float2(1,0),float2(127.1,311.7)),
 dot(i+float2(0,1),float2(127.1,311.7)),
 dot(i+float2(1,1),float2(127.1,311.7))))*43758.5453);
float grain = lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y);
float damp = smoothstep(-0.6,0.8,sin(UV.x*3.7+sin(UV.y*2.1))*cos(UV.y*4.2));
return float4(float3(0.025,0.029,0.034)*(0.65+grain*0.65)*(1.0-damp*0.4),lerp(0.82,0.42,damp));
'''

def install(imp):
    source=ROOT/'Authored/Textures/T_Reception_NightStreet.png'
    key=hashlib.sha256(source.read_bytes()).hexdigest()+':streamed-bc7-pot-v1'
    path=BASE+'/Textures/T_Reception_NightStreet'
    tex=imp.reuse(path,key)
    if not tex:
        tex=imp.imported(path,source)
        for k,v in dict(srgb=True,never_stream=False,compression_settings=u.TextureCompressionSettings.TC_BC7,
            lod_group=u.TextureGroup.TEXTUREGROUP_WORLD,max_texture_size=2048,
            power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,
            address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP).items():tex.set_editor_property(k,v)
        imp.saved(tex,key)

    def material(name,key,unlit=False):
        path=BASE+'/Materials/'+name
        prior=imp.reuse(path,key)
        if prior:return prior,None
        m=imp.A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        m.set_editor_property('used_with_instanced_static_meshes',True)
        if unlit:
            m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
            m.set_editor_property('two_sided',True)
        slab=L.create_material_expression(m,u.MaterialExpressionSubstrateUnlitBSDF if unlit else u.MaterialExpressionSubstrateShadingModels)
        if not unlit:slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        return m,slab

    def node(m,kind,**props):
        n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin='',out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Unable to connect material input '+pin)
    def custom(m,code,inputs,kind,desc):
        n=node(m,'Custom',code=code,output_type=kind,desc=desc)
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins)
        for key,src in inputs.items():wire(src,n,key)
        return n
    def complete(m,key):
        L.layout_material_expressions(m)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Unable to compile '+m.get_path_name()+': '+str(errors))
        imp.saved(m,key)

    key=hashlib.sha256((PROJECTION+':substrate-night-luminance1.6-v1').encode()).hexdigest()
    m,slab=material('M_NightStreet_Background',key,True)
    if slab:
        def instance_position(src):
            n=node(m,'TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
            wire(src,n);return n
        # Per-instance space is essential: each dungeon module can rotate and
        # translate, and its parts are drawn through InstancedStaticMeshComponents.
        position=instance_position(node(m,'WorldPosition'))
        eye=instance_position(node(m,'CameraPositionWS'))
        uv=custom(m,PROJECTION,dict(P=position,Eye=eye),u.CustomMaterialOutputType.CMOT_FLOAT2,'Street projected to a virtual plane; one image sample')
        sample=node(m,'TextureSampleParameter2D',parameter_name='NightStreet',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire(uv,sample,'UVs')
        # Edge fade avoids stretched border pixels at extreme grille-side views.
        fade=custom(m,'float2 d=max(-UV,UV-1.0); return saturate(1.0-max(d.x,d.y)*8.0);',dict(UV=uv),u.CustomMaterialOutputType.CMOT_FLOAT1,'Fade beyond photograph boundary')
        brightness=node(m,'ScalarParameter',parameter_name='NightLuminance',default_value=1.6)
        gain=node(m,'Multiply');wire(fade,gain,'A');wire(brightness,gain,'B')
        emission=node(m,'Multiply');wire(sample,emission,'A','RGB');wire(gain,emission,'B')
        wire(emission,slab,'EmissiveColor');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        wire(node(m,'Constant3Vector',constant=u.LinearColor(0,0,0,1)),slab,'TransmittanceColor')
        complete(m,key)

    key=hashlib.sha256((ASPHALT+':substrate-asphalt-v1').encode()).hexdigest()
    m,slab=material('M_NightStreet_Asphalt',key)
    if slab:
        surface=custom(m,ASPHALT,dict(UV=node(m,'TextureCoordinate')),u.CustomMaterialOutputType.CMOT_FLOAT4,'Fine aggregate and damp roughness; metres UV')
        color=node(m,'ComponentMask',r=True,g=True,b=True,a=False);wire(surface,color)
        rough=node(m,'ComponentMask',r=False,g=False,b=False,a=True);wire(surface,rough)
        for src,pin,prop in [(color,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),(rough,'Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
            wire(src,slab,pin);L.connect_material_property(src,'',prop)
        wire(node(m,'Constant',r=0.),slab,'Metallic')
        complete(m,key)
