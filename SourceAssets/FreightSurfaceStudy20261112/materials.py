"""Local material study. Only the two focal surface bindings consume these assets."""
from pathlib import Path
import types
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE='/Game/SceneTests/FreightSurfaceStudy20261112'
REV='freight_surface_study_20261112'
source=(ROOT.parent/'FacilitySurfaceUpgrade20261108/assets.py').read_text('utf8').split("GRAIN='/Game/")[0]
source=source.replace('from recipe import ROOT,BASE,REVISION,canonical,resolve','').replace("SOURCE=json.loads((ROOT/'material-inputs.json').read_text('utf8'))","SOURCE={}").replace('FacilitySurface.Owner','FreightSurfaceStudy.Owner')
env=dict(ROOT=ROOT,BASE=BASE,REVISION=REV,canonical=lambda path:path.split('.')[0])
exec(compile(source,'scoped_graph_functions','exec'),env)
H=types.SimpleNamespace(**env)
L=u.MaterialEditingLibrary

def loaded(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing source '+path)
    return obj

def tex(m,kind,param,path,mode):
    return H.node(m,kind,parameter_name=param,texture=loaded(path),sampler_type=mode)
def mode_color(path):
    texture=loaded(path)
    if texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_MASKS:
        return u.MaterialSamplerType.SAMPLERTYPE_MASKS
    if texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_GRAYSCALE:
        return (u.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE if texture.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    return u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
def make():
    scan='/Game/Dungeons/FacilityQuixel20261108/DamagedConcrete/Textures/T_DamagedConcrete_'
    # Registered scan colour, alpha, tangent normals and ORM accompany the derived geometry.
    m=H.own('Materials/M_PackingConcreteRelief')
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    m.set_editor_property('opacity_mask_clip_value',.38)
    color=tex(m,'TextureSampleParameter2D','ColorCoverage',scan+'BaseOpacity',mode_color(scan+'BaseOpacity'))
    normal=tex(m,'TextureSampleParameter2D','ScanNormal',scan+'Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm=tex(m,'TextureSampleParameter2D','ScanORM',scan+'ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    for out,prop in [('RGB','BASE_COLOR'),('A','OPACITY_MASK')]:H.output(color,prop,out)
    H.output(normal,'NORMAL','RGB')
    for out,prop in [('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')]:H.output(orm,prop,out)
    H.save(m)
    c=H.own('Materials/M_CartCoatingWear')
    L.delete_all_material_expressions(c)
    s=H.spatial(c)
    rust='/Game/SD_Art/Industrial_Infrastructure/Materials/Rust/Textures/T_Tiling_Rust_'
    noise='/Game/UndergroundTunnel/Textures/Effects/T_Noise01a'
    s.update(RustC=tex(c,'TextureObjectParameter','OxideColor',rust+'Albedo',mode_color(rust+'Albedo')),
             RustR=tex(c,'TextureObjectParameter','OxideORM',rust+'ORM',mode_color(rust+'ORM')),
             RustN=tex(c,'TextureObjectParameter','OxideNormal',rust+'Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
             Field=tex(c,'TextureObjectParameter','WearBreakup',noise,mode_color(noise)),
             PaintTint=H.node(c,'VectorParameter',parameter_name='PaintTint',default_value=u.LinearColor(.115,.143,.122,1.)),
             RustAmount=H.scalar(c,'RustAmount',1.),RustValue=H.scalar(c,'RustValue',.86))
    s.pop('ViewLocal',None)
    result=H.custom(c,(ROOT/'cart_coating.ush').read_text('utf8'),s,4,extra=[('NormalLocal',3),('MetalOut',1),('AOOut',1)])
    c.set_editor_property('tangent_space_normal',False)
    for channels,prop in [((True,True,True,False),'BASE_COLOR'),((False,False,False,True),'ROUGHNESS')]:
        rr,gg,bb,aa=channels;mask=H.node(c,'ComponentMask',r=rr,g=gg,b=bb,a=aa);H.wire(result,mask);H.output(mask,prop)
    transform=H.node(c,'Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    H.wire(result,transform,out='NormalLocal');H.output(transform,'NORMAL')
    H.output(result,'METALLIC','MetalOut');H.output(result,'AMBIENT_OCCLUSION','AOOut')
    L.set_base_material_usage(c,u.MaterialUsage.MATUSAGE_NANITE,True)
    H.save(c)
    return m,H.instance('CartCoatingWear',c)
