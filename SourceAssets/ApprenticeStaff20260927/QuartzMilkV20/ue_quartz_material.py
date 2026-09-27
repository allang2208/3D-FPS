"""Material-only cloudy quartz recipe; no geometry or gameplay edits."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'quartz_parameters.json').read_text())
DEST='/Game/Weapons/ApprenticeStaff20260927/QuartzMilkV20/Materials'
L=u.MaterialEditingLibrary

def build_quartz_material(rebuild=False):
    m=u.load_asset(DEST+'/'+P['material'])
    if m and not rebuild:return m
    if not m:m=u.AssetToolsHelpers.get_asset_tools().create_asset(P['material'],DEST,u.Material,u.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create quartz material')
    L.delete_all_material_expressions(m)
    def node(cls,**props):
        n=L.create_material_expression(m,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def color(v):return node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def scalar(v):return node(u.MaterialExpressionConstant,r=v)
    def wire(a,channel,b,pin):
        if not L.connect_material_expressions(a,channel,b,pin):raise RuntimeError('Cannot wire '+pin)
    def output(n,prop):
        if not L.connect_material_property(n,'',prop):raise RuntimeError('Cannot connect '+str(prop))
    def ramp(n,lo,hi):
        multiply=node(u.MaterialExpressionMultiply,const_b=hi-lo);wire(n,'',multiply,'A')
        add=node(u.MaterialExpressionAdd,const_b=lo);wire(multiply,'',add,'A');return add
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property('two_sided',False)
    world=node(u.MaterialExpressionWorldPosition)
    local=node(u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world,'',local,str(L.get_material_expression_input_names(local)[0]))
    scale=node(u.MaterialExpressionMultiply);wire(local,'',scale,'A');wire(color(P['local_cloud_frequency']),'',scale,'B')
    # Fast 3-D gradient: two small octaves, attached to the object, no animation.
    noise_type=next(getattr(u.NoiseFunction,n) for n in dir(u.NoiseFunction) if 'GRADIENT' in n and 'TEX' in n and '3' in n)
    noise=node(u.MaterialExpressionNoise,scale=1.,quality=1,levels=P['noise_levels'],noise_function=noise_type,output_min=0.,output_max=1.)
    wire(scale,'',noise,str(L.get_material_expression_input_names(noise)[0]))
    thin=node(u.MaterialExpressionThinTranslucentMaterialOutput)
    wire(color(P['transmittance']),'',thin,str(L.get_material_expression_input_names(thin)[0]))
    output(color(P['base_color']),u.MaterialProperty.MP_BASE_COLOR)
    output(ramp(noise,P['opacity_min'],P['opacity_max']),u.MaterialProperty.MP_OPACITY)
    output(ramp(noise,P['roughness_min'],P['roughness_max']),u.MaterialProperty.MP_ROUGHNESS)
    output(scalar(P['specular']),u.MaterialProperty.MP_SPECULAR)
    output(scalar(0),u.MaterialProperty.MP_METALLIC)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Quartz material compilation failed: '+str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Cannot save quartz material')
    return m
