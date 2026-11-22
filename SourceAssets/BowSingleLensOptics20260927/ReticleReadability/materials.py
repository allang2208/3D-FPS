"""Reusable physical-glass reticle shader for the two bow optics."""
from pathlib import Path
import runpy
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
    # The two fixed bow engravings use their own glass UVs and original green finish.
    family={2:10,4:11}[power]
    etching=f"const int family = {family};\n"+(P/'Reticle.hlsl').read_text(encoding='utf8')
    shape=node(m,u.MaterialExpressionCustom,code=etching,
               description='Fixed bow engraving on glass UVs',
               output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    uv_pin=u.CustomInput();uv_pin.set_editor_property('input_name','UV')
    shape.set_editor_property('inputs',[uv_pin])
    wire(uv,shape,'UV')
    outline=node(m,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False);wire(shape,outline,'')
    zero,one=scalar(m,0),scalar(m,1)
    glass=color(m,(.73,.92,.77) if power==2 else (.69,.87,.76))
    output(zero,u.MaterialProperty.MP_METALLIC)
    fresnel=node(m,u.MaterialExpressionFresnel,exponent=5.,base_reflect_fraction=.015)
    mul=node(m,u.MaterialExpressionMultiply,const_b=.20);wire(fresnel,mul,'A')
    add=node(m,u.MaterialExpressionAdd,const_b=.035);wire(mul,add,'A')
    opacity=mix(m,add,one,outline)
    output(opacity,u.MaterialProperty.MP_OPACITY)
    solid=node(m,u.MaterialExpressionDivide);wire(outline,solid,'A');wire(opacity,solid,'B')
    output(mix(m,glass,color(m,(0.,0.,0.)),solid),u.MaterialProperty.MP_BASE_COLOR)
    output(mix(m,scalar(m,.045),one,solid),u.MaterialProperty.MP_ROUGHNESS)
    output(mix(m,scalar(m,.5),zero,solid),u.MaterialProperty.MP_SPECULAR)
    output(one,u.MaterialProperty.MP_REFRACTION)
    # UE applies glass opacity during blending. Divide once to preserve subpixel ink.
    palette=(P/'ReticleInk.hlsl').read_text(encoding='utf8')
    emission=node(m,u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
        code=palette+f'\nreturn glassInk.Shade(Etch,{family}.,float4(0.,0.,0.,0.),0.)/max(Opacity,.001);')
    pins=[]
    for name in ('Etch','Opacity'):
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    emission.set_editor_property('inputs',pins)
    wire(shape,emission,'Etch');wire(opacity,emission,'Opacity')
    inverse=node(m,u.MaterialExpressionEyeAdaptationInverse)
    names=[str(n) for n in L.get_material_expression_input_names(inverse)]
    wire(emission,inverse,names[0]);wire(one,inverse,names[1])
    output(inverse,u.MaterialProperty.MP_EMISSIVE_COLOR)
    runpy.run_path(str(P.parents[1]/'SharedPhysicalOptics20261030/late_glass.py'))['configure_late_glass'](m)
