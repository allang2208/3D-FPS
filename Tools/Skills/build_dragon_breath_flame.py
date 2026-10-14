"""Airborne animated flame; the rejected ground-fire/smoke-card R3 is archived.

Reuse the project's existing FireFlame 8x8 source, also used by the fireball
mantle. Keep this skill's material independent of all accepted fireball assets.
"""
import unreal as u
from build_fireball_assets import LIB,TOOLS


def connect(src,dst,pin,out=''):
    if not LIB.connect_material_expressions(src,out,dst,pin):
        raise RuntimeError('Dragon flame connection failed: '+dst.get_name()+'/'+pin)


def custom(mat,code,typ,inputs,x,y):
    n=LIB.create_material_expression(mat,u.MaterialExpressionCustom,x,y)
    n.set_editor_property('output_type',typ)
    pins=[]
    for name,source,output in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins);n.set_editor_property('code',code)
    for name,source,output in inputs:connect(source,n,name,output)
    return n


def build_flame_material(dest,source,persist):
    eal=u.EditorAssetLibrary
    name='M_DragonFlame'
    mat=u.load_asset(dest+'/'+name) if eal.does_asset_exist(dest+'/'+name) else TOOLS.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ALPHA_COMPOSITE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('disable_depth_test',False)
    LIB.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True)
    uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-1200,0)
    age=LIB.create_material_expression(mat,u.MaterialExpressionParticleRelativeTime,-1200,360)
    pixel_depth=LIB.create_material_expression(mat,u.MaterialExpressionPixelDepth,-1200,540)
    color=LIB.create_material_expression(mat,u.MaterialExpressionParticleColor,-1200,720)
    atlas=LIB.create_material_expression(mat,u.MaterialExpressionTextureSampleParameterSubUV,-850,0)
    atlas.set_editor_property('parameter_name','JetFlameAtlas')
    tex=u.load_asset('/Game/_SplineVFX/_GenericSource/Texture/T_Vfx_Stamp_FireFlame_88')
    if not tex:raise RuntimeError('Missing existing FireFlame atlas')
    atlas.set_editor_property('texture',tex)
    atlas.set_editor_property('blend',True)
    atlas.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    gain=LIB.create_material_expression(mat,u.MaterialExpressionScalarParameter,-600,240)
    gain.set_editor_property('parameter_name','FlameEmission');gain.set_editor_property('default_value',1.7)
    rgba=custom(mat,'''float2 q=frac(UV*8.0);
// RGB flame on black. Keep actual animated tongues; no opaque ground tile.
float edge=smoothstep(0.0,.075,q.x)*(1.0-smoothstep(.925,1.0,q.x));
edge*=smoothstep(0.0,.025,q.y)*(1.0-smoothstep(.68,.96,q.y));
float brightness=max(Fire.r,max(Fire.g,Fire.b));
float coverage=sqrt(saturate(brightness))*edge;
// Zero-age spawn cards are invisible, including before ParticleUpdate runs.
float birth=smoothstep(0.0,.045,Age);
float nearFade=smoothstep(18.0,45.0,CameraDepth);
float alpha=.78*coverage*ParticleAlpha*birth*nearFade;
return float4(Fire*Gain,saturate(alpha));
''',u.CustomMaterialOutputType.CMOT_FLOAT4,[('UV',uv,''),('Fire',atlas,'RGB'),('Age',age,''),('ParticleAlpha',color,'A'),('Gain',gain,''),('CameraDepth',pixel_depth,'')],-180,300)
    rgb=LIB.create_material_expression(mat,u.MaterialExpressionComponentMask,80,100)
    for p,v in [('r',True),('g',True),('b',True),('a',False)]:rgb.set_editor_property(p,v)
    connect(rgba,rgb,str(LIB.get_material_expression_input_names(rgb)[0]))
    alpha=LIB.create_material_expression(mat,u.MaterialExpressionComponentMask,80,450)
    for p,v in [('r',False),('g',False),('b',False),('a',True)]:alpha.set_editor_property(p,v)
    connect(rgba,alpha,str(LIB.get_material_expression_input_names(alpha)[0]))
    depth=LIB.create_material_expression(mat,u.MaterialExpressionDepthFade,300,450)
    depth.set_editor_property('fade_distance_default',6.0)
    connect(alpha,depth,str(LIB.get_material_expression_input_names(depth)[0]))
    premultiplied=LIB.create_material_expression(mat,u.MaterialExpressionMultiply,300,100)
    connect(rgb,premultiplied,'A');connect(depth,premultiplied,'B')
    exposure=LIB.create_material_expression(mat,u.MaterialExpressionEyeAdaptationInverse,500,100)
    connect(premultiplied,exposure,str(LIB.get_material_expression_input_names(exposure)[0]))
    if not LIB.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Missing flame emission')
    if not LIB.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('Missing flame opacity')
    errors=LIB.recompile_material(mat)
    if errors:raise RuntimeError('Dragon flame shader: '+str(errors))
    if not u.PoisonMaggotMonster.compile_material_assets([mat]):raise RuntimeError('Dragon flame compile failed')
    persist(mat)
    name='MI_DragonFlame'
    instance=u.load_asset(dest+'/'+name) if eal.does_asset_exist(dest+'/'+name) else TOOLS.create_asset(name,dest,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance,mat)
    LIB.set_material_usage_override(instance,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True,True)
    LIB.set_material_instance_scalar_parameter_value(instance,'FlameEmission',1.7)
    LIB.update_material_instance(instance);persist(instance)
    return instance
