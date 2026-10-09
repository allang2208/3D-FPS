"""Street image boundary repair: never display clamped edge texels as scenery."""
from pathlib import Path
import hashlib
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreetEdgeFix20261009'
MATERIAL=BASE+'/Materials/M_NightStreet_BackgroundV2'
TEXTURE='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009/Textures/T_Reception_NightStreet'
L=u.MaterialEditingLibrary

PROJECTION=r'''
float3 ray = P - Eye;
float3 distant = Eye + ray * ((-3800.0 - Eye.x) / min(ray.x,-0.1));
// Additional image coverage for close grille views, preserving the 2:1 aspect.
return float2(0.5 - distant.y / 2640.0, 0.53 - (distant.z - 165.0) / 1320.0);
'''
COMPOSITE=r'''
// Fade INSIDE the photo. Outside it, image weight is exactly zero; clamp mode
// cannot extend the last rows/columns into vertical or horizontal streaks.
float2 border = min(UV,1.0-UV);
float2 coverage = smoothstep(float2(0.008,0.008),float2(0.080,0.070),border);
float photograph = coverage.x * coverage.y;

// The floor of the shallow enclosure is real near-ground, not a continuation
// of the distant image. Blend the bottom of each vertical face into that floor.
float groundJoin = smoothstep(2.0,32.0,P.z);
photograph *= groundJoin;

// A smooth, detail-free night surround avoids copying image-edge lamp/window
// patterns. Keep the horizon consistent with the photograph's original centre.
float sky = 1.0-smoothstep(0.38,0.64,UV.y);
float3 surround = lerp(float3(0.003,0.0045,0.006),float3(0.008,0.013,0.024),sky);
float horizon = exp2(-abs(UV.y-0.53)*16.0);
surround += float3(0.002,0.0025,0.003)*horizon;
surround = lerp(float3(0.003,0.004,0.005),surround,groundJoin);
return lerp(surround,Image,photograph)*Luminance;
'''

def install(imp):
    key=hashlib.sha256((PROJECTION+COMPOSITE+':inside-feather-v2').encode()).hexdigest()
    prior=imp.reuse(MATERIAL,key)
    if prior:return prior
    m=imp.A.create_asset(MATERIAL.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    def node(kind,**props):
        n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin='',out=''):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material input connection failed: '+pin)
    def custom(code,inputs,output,desc):
        n=node('Custom',code=code,output_type=output,desc=desc)
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins)
        for key,src in inputs.items():
            if isinstance(src,tuple):wire(src[0],n,key,src[1])
            else:wire(src,n,key)
        return n
    def local(src):
        n=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
            transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
        wire(src,n);return n
    p=local(node('WorldPosition'));eye=local(node('CameraPositionWS'))
    uv=custom(PROJECTION,dict(P=p,Eye=eye),u.CustomMaterialOutputType.CMOT_FLOAT2,'Aspect-correct distant street in module instance space')
    safe=custom('return clamp(UV,float2(0.5/2048.0,0.5/1024.0),float2(1.0-0.5/2048.0,1.0-0.5/1024.0));',
        dict(UV=uv),u.CustomMaterialOutputType.CMOT_FLOAT2,'Safe sample UV; photograph mask uses the original unclamped UV')
    sample=node('TextureSampleParameter2D',parameter_name='NightStreet',texture=imp.asset(TEXTURE),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    wire(safe,sample,'UVs')
    luminance=node('ScalarParameter',parameter_name='NightLuminance',default_value=1.6)
    emission=custom(COMPOSITE,dict(UV=uv,P=p,Image=(sample,'RGB'),Luminance=luminance),
        u.CustomMaterialOutputType.CMOT_FLOAT3,'Inside-edge feather, analytic night surround and grounded floor join')
    slab=node('SubstrateUnlitBSDF')
    wire(emission,slab,'EmissiveColor');wire(node('Constant3Vector',constant=u.LinearColor(0,0,0,1)),slab,'TransmittanceColor')
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Night boundary material build failed: '+str(errors))
    return imp.saved(m,key)
