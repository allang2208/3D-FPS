"""UE recipe for the textured brown woven/waxed finishes; shared maps stay read-only."""
import unreal as u
L=u.MaterialEditingLibrary
def build_linen(mat,waxed=False):
    root='/Game/Weapons/DarkBow20260925/GripSeriesV20/Textures/T_Bow_Grip_WovenLinen_'
    L.delete_all_material_expressions(mat)
    def node(cls,**values):
        n=L.create_material_expression(mat,cls)
        for k,v in values.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin,channel=''):
        if not L.connect_material_expressions(a,channel,b,pin):raise RuntimeError('Linen connection '+pin)
    def output(a,prop,channel=''):
        if not L.connect_material_property(a,channel,prop):raise RuntimeError('Linen material output '+str(prop))
    samples={}
    for kind,sampler in [('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS),('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
        texture=u.load_asset(root+kind)
        if not texture:raise RuntimeError('Missing shared linen '+kind)
        samples[kind]=node(u.MaterialExpressionTextureSample,texture=texture,sampler_type=sampler)
    tint=node(u.MaterialExpressionMultiply,const_b=.8 if waxed else 1.)
    wire(samples['BaseColor'],tint,'A','RGB');output(tint,u.MaterialProperty.MP_BASE_COLOR)
    rough=node(u.MaterialExpressionMultiply,const_b=.92 if waxed else 1.)
    wire(samples['ORM'],rough,'A','G');output(rough,u.MaterialProperty.MP_ROUGHNESS)
    output(samples['ORM'],u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R')
    output(node(u.MaterialExpressionConstant,r=0),u.MaterialProperty.MP_METALLIC)
    normal=node(u.MaterialExpressionMultiply);wire(samples['Normal'],normal,'A','RGB')
    strength=.5 if waxed else .7
    wire(node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(strength,strength,1,1)),normal,'B')
    normalized=node(u.MaterialExpressionNormalize);wire(normal,normalized,'VectorInput');output(normalized,u.MaterialProperty.MP_NORMAL)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Linen material compile '+str(errors))
