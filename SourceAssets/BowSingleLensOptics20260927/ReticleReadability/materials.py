"""Reusable physical-glass reticle shader for the two bow optics."""
from pathlib import Path
import unreal as u
L=u.MaterialEditingLibrary
P=Path(__file__).parent

def node(m,cls,**values):
    n=L.create_material_expression(m,cls)
    for key,value in values.items():n.set_editor_property(key,value)
    return n
def wire(src,dst,pin,channel=''):
    if not L.connect_material_expressions(src,channel,dst,pin):raise RuntimeError('Connection failed '+pin)
def output(src,prop,channel=''):
    if not L.connect_material_property(src,channel,prop):raise RuntimeError('Material output failed '+str(prop))
def scalar(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def color(m,rgb):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1))
def mix(m,a,b,weight):
    n=node(m,u.MaterialExpressionLinearInterpolate);wire(a,n,'A');wire(b,n,'B');wire(weight,n,'Alpha');return n

def hide_old_etching(m):
    # Retain the original section, but remove its subpixel geometry from depth/colour.
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    output(scalar(m,0),u.MaterialProperty.MP_OPACITY_MASK)
    output(color(m,(0,0,0)),u.MaterialProperty.MP_BASE_COLOR)

def configure_temporal_response(m,outline):
    # Only opaque reticle coverage writes lens depth/rigid motion. Clear glass
    # opacity is <= .235, below this threshold, preserving the scene behind it.
    m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    m.set_editor_property('output_translucent_velocity',True)
    m.set_editor_property('is_translucency_velocity_from_depth',False)
    m.set_editor_property('opacity_mask_clip_value',.333)
    m.set_editor_property('disable_depth_test',False)
    # Responsive AA is a whole-pane TAA flag, not a per-reticle TSR control.
    # Use the project's enabled TemporalResponsiveness output locally instead.
    m.set_editor_property('enable_responsive_aa',False)
    response=node(m,u.MaterialExpressionTemporalResponsivenessOutput)
    strength=node(m,u.MaterialExpressionMultiply,const_b=.75,
                  desc='Bow reticle: local temporal response, clear glass excluded')
    wire(outline,strength,'A');wire(strength,response,'')
    u.EditorAssetLibrary.set_metadata_tag(m,'BowReticleTemporalVersion','coverage-velocity-v1')

def build_lens(m,power):
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('two_sided',False)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    shape=node(m,u.MaterialExpressionCustom,code=(P/'Reticle.hlsl').read_text(encoding='utf8'),
               description='Fine etched reticle: restrained green centre, dim outer guides, narrow AA edge',
               output_type=u.CustomMaterialOutputType.CMOT_FLOAT2)
    pins=[]
    for name in ['UV','FourPower']:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    shape.set_editor_property('inputs',pins)
    wire(uv,shape,'UV');wire(scalar(m,1 if power==4 else 0),shape,'FourPower')
    core=node(m,u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False);wire(shape,core,'')
    outline=node(m,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False);wire(shape,outline,'')
    configure_temporal_response(m,outline)
    zero,one=scalar(m,0),scalar(m,1)
    glass=color(m,(.80,.92,.95) if power==2 else (.88,.84,.96))
    output(mix(m,glass,color(m,(.003,.004,.005)),outline),u.MaterialProperty.MP_BASE_COLOR)
    output(zero,u.MaterialProperty.MP_METALLIC)
    output(mix(m,scalar(m,.045),scalar(m,1.),outline),u.MaterialProperty.MP_ROUGHNESS)
    output(mix(m,scalar(m,.5),zero,outline),u.MaterialProperty.MP_SPECULAR)
    fresnel=node(m,u.MaterialExpressionFresnel,exponent=5.,base_reflect_fraction=.015)
    mul=node(m,u.MaterialExpressionMultiply,const_b=.20);wire(fresnel,mul,'A')
    add=node(m,u.MaterialExpressionAdd,const_b=.035);wire(mul,add,'A')
    output(mix(m,add,one,outline),u.MaterialProperty.MP_OPACITY)
    output(one,u.MaterialProperty.MP_REFRACTION)
    emission=node(m,u.MaterialExpressionMultiply);wire(color(m,(.035,.36,.055)),emission,'A');wire(core,emission,'B')
    inverse=node(m,u.MaterialExpressionEyeAdaptationInverse)
    names=[str(n) for n in L.get_material_expression_input_names(inverse)]
    wire(emission,inverse,names[0]);wire(one,inverse,names[1])
    output(inverse,u.MaterialProperty.MP_EMISSIVE_COLOR)
