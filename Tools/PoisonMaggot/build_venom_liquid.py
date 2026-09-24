"""Author the venom's wet surface, fine mist and impact film. No gameplay/preview.

All shapes/noise are original procedural material code. Run with
-run=pythonscript -AllowCommandletRendering to compile the actual Substrate shaders.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/PoisonMaggotVenom20260915'
DEST = '/Game/Monsters/PoisonMaggot/VenomLiquid20260915'
LIB = u.MaterialEditingLibrary
ASSETS = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SOURCE.mkdir(parents=True, exist_ok=True)
ASSETS.make_directory(DEST)
CREATED = []

# Local functions inside a struct work in a Material Custom expression.
NOISE = '''struct VenomNoise {
float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float noise(float2 p) {
 float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
 return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
             lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
float fbm(float2 p) {return .57*noise(p)+.28*noise(p*2.07+5.3)+.15*noise(p*4.13+17.1);}
}; VenomNoise vn;
'''

def node(mat, cls, **props):
    n = LIB.create_material_expression(mat, cls)
    for key, value in props.items(): n.set_editor_property(key, value)
    return n

def wire(src, dst, pin):
    expr, out = src if isinstance(src, tuple) else (src, '')
    if isinstance(pin, int): pin = str(LIB.get_material_expression_input_names(dst)[pin])
    if not LIB.connect_material_expressions(expr, out, dst, pin):
        raise RuntimeError('Cannot connect material input ' + pin)

def output(src, prop):
    if not LIB.connect_material_property(src, '', getattr(u.MaterialProperty, 'MP_' + prop)):
        raise RuntimeError('Cannot connect material output ' + prop)

def constant(mat, value):
    return node(mat, u.MaterialExpressionConstant, r=value)

def scalar(mat, name, value):
    return node(mat, u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)

def custom(mat, label, code, inputs, width=1):
    (SOURCE / (label + '.hlsl')).write_text(code + '\n', encoding='utf-8')
    n = node(mat, u.MaterialExpressionCustom, code=code,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    n.set_editor_property('inputs', pins)
    for name, source in inputs.items(): wire(source, n, name)
    return n

def material(name, translucent=False, decal=False, instanced=False):
    path = DEST + '/' + name
    mat = u.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT if translucent else u.BlendMode.BLEND_OPAQUE)
    if decal: mat.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    if translucent and not decal:
        mat.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
        mat.set_editor_property('output_translucent_velocity', False)
        mat.set_editor_property('is_translucency_velocity_from_depth', False)
        mat.set_editor_property('disable_depth_test', False)
    if instanced: LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    return mat

def surface(mat, inputs, decal=False):
    # FPSGAME uses Substrate: wire opacity into the actual front material too.
    slab = node(mat, u.MaterialExpressionSubstrateShadingModels,
                shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mapping = {'BASE_COLOR':'BaseColor', 'NORMAL':'Normal', 'ROUGHNESS':'Roughness',
               'SPECULAR':'Specular', 'OPACITY':'Opacity', 'EMISSIVE_COLOR':'Emissive Color'}
    for prop, value in inputs.items():
        output(value, prop); wire(value, slab, mapping[prop])
    if decal:
        conversion = node(mat, u.MaterialExpressionSubstrateConvertToDecal)
        wire(slab, conversion, 0)
        output(conversion, 'FRONT_MATERIAL')
    else:
        output(slab, 'FRONT_MATERIAL')

def finish(mat):
    LIB.layout_material_expressions(mat)
    errors = LIB.recompile_material(mat)
    if errors: raise RuntimeError(mat.get_name() + ': ' + '; '.join(errors))
    if not ASSETS.save_loaded_asset(mat, False): raise RuntimeError('Could not save ' + mat.get_path_name())
    CREATED.append(mat.get_path_name())
    u.log('VENOM_LIQUID_ASSET_SAVED ' + mat.get_path_name())

def liquid(name, shell=False, drops=False):
    mat = material(name, translucent=shell, instanced=drops)
    uv = node(mat, u.MaterialExpressionTextureCoordinate)
    time = node(mat, u.MaterialExpressionTime)
    flow = custom(mat, name + '_flow', NOISE + '''
float2 p=UV*float2(5,3)+float2(T*.09,-T*.06);
return vn.fbm(p+float2(vn.noise(p*.8),vn.noise(p*.8+4))*.5);
''', {'UV':uv, 'T':time})
    base = custom(mat, name + '_color', '''
return lerp(float3(.018,.030,.003),float3(.095,.145,.013),smoothstep(.15,.85,N));
''', {'N':flow}, 3)
    normal = custom(mat, name + '_normal', NOISE + '''
float2 p=UV*float2(8,5)+float2(T*.13,-T*.085);
float h=vn.fbm(p),dx=vn.fbm(p+float2(.035,0))-h,dy=vn.fbm(p+float2(0,.035))-h;
return normalize(float3(-dx*1.8,-dy*1.8,1));
''', {'UV':uv, 'T':time}, 3)
    rough = custom(mat, name + '_roughness', 'return lerp(.09,.22,N);', {'N':flow})
    inputs = {'BASE_COLOR':base, 'NORMAL':normal, 'ROUGHNESS':rough, 'SPECULAR':constant(mat,.62)}
    if shell:
        fresnel = node(mat, u.MaterialExpressionFresnel, exponent=2.2, base_reflect_fraction=.04)
        inputs['OPACITY'] = custom(mat, name + '_opacity', 'return lerp(.89,.36,F)*(.86+.14*N);', {'F':fresnel,'N':flow})
        vertex = node(mat, u.MaterialExpressionVertexNormalWS)
        amplitude = scalar(mat, 'SurfaceRippleCM', .36)
        wobble = custom(mat, name + '_wobble', '''
float a=sin(UV.x*18.84956+T*8.1+sin(UV.y*12.56637-T*3.4));
float b=sin(UV.y*18.84956-T*6.2)*sin(UV.x*12.56637+T*2.7);
return Normal*Amplitude*(a*.65+b*.35);
''', {'UV':uv, 'T':time, 'Normal':vertex, 'Amplitude':amplitude}, 3)
        output(wobble, 'WORLD_POSITION_OFFSET')
    surface(mat, inputs); finish(mat)

liquid('M_VenomLiquid', shell=True)
liquid('M_VenomCore')
liquid('M_VenomDroplet', drops=True)

mist = material('M_VenomMist', translucent=True, instanced=True)
mist.set_editor_property('two_sided', True)
mist.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
uv = node(mist, u.MaterialExpressionTextureCoordinate)
time = node(mist, u.MaterialExpressionTime)
data = node(mist, u.MaterialExpressionPerInstanceCustomData, data_index=0, const_default_value=0.)
alpha = node(mist, u.MaterialExpressionVertexInterpolator); wire(data, alpha, 0)
variant_data = node(mist, u.MaterialExpressionPerInstanceCustomData, data_index=1, const_default_value=0.)
variant = node(mist, u.MaterialExpressionVertexInterpolator); wire(variant_data, variant, 0)
mask = custom(mist, 'MistOpacity', NOISE + '''
float2 p=(UV-.5)*2;
float2 q=p*2.5+float2(Variant*13+T*.09,Variant*7-T*.15);
float n=vn.fbm(q+float2(vn.noise(q+2),vn.noise(q+9))*.8);
float radius=length(p)+(.5-n)*.28;
return pow(saturate(1-radius),1.7)*smoothstep(.20,.78,n)*Alpha;
''', {'UV':uv,'T':time,'Variant':variant,'Alpha':alpha})
fade = node(mist, u.MaterialExpressionDepthFade, fade_distance_default=5.)
wire(mask, fade, 'Opacity')
tint = node(mist, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.17,.195,.055,1))
surface(mist, {'BASE_COLOR':tint,'OPACITY':fade,'ROUGHNESS':constant(mist,1.),'SPECULAR':constant(mist,0.)})
finish(mist)

wet = material('M_VenomWetFilm', translucent=True, decal=True)
uv = node(wet, u.MaterialExpressionTextureCoordinate)
life = node(wet, u.MaterialExpressionDecalLifetimeOpacity)
mask = custom(wet, 'WetFilmCoverage', NOISE + '''
float2 p=(UV-.5)*2;float angle=atan2(p.y,p.x);
float boundary=.61+.09*sin(angle*5+.4)+.065*sin(angle*9-1.1);
float d=length(p)-boundary-(vn.fbm(p*8)-.5)*.10;
float coverage=1-smoothstep(-.015,.035,d);
for(int i=0;i<7;i++) {
 float a=float(i)*2.39996+.6;float2 center=float2(cos(a),sin(a))*(.68+.11*vn.hash(float2(i,2)));
 float r=.025+.04*vn.hash(float2(i,5));
 coverage=max(coverage,1-smoothstep(r*.65,r,length(p-center)));
}
return saturate(coverage)*Life*.82;
''', {'UV':uv,'Life':life})
base = custom(wet, 'WetFilmColor', NOISE + '''
float n=vn.fbm(UV*8);
return lerp(float3(.014,.025,.002),float3(.065,.091,.009),n);
''', {'UV':uv}, 3)
rough = custom(wet, 'WetFilmRoughness', 'return lerp(.62,.12,Life);', {'Life':life})
surface(wet, {'BASE_COLOR':base,'OPACITY':mask,'ROUGHNESS':rough,'SPECULAR':constant(wet,.58)}, decal=True)
finish(wet)

# Keep the current flowing mist and seeded cosmetic residue on full rebuilds.
import sys
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from author_impact_smoke_corrosion import smoke_material,wet_film
smoke_material(True);wet_film()

# This waits for authoring/compilation only; it does not execute a game or render.
materials = [u.load_asset(path) for path in CREATED]
if not u.PoisonMaggotMonster.compile_material_assets(materials):
    raise RuntimeError('Venom material compilation failed')
for asset in materials: ASSETS.save_loaded_asset(asset, False)
(SOURCE/'authoring.json').write_text(json.dumps({
    'assets':CREATED, 'source':'Original procedural HLSL; engine BasicShapes sphere and plane',
    'presentation':'Turbid olive liquid shell and core, shrinking wet droplets, sparse lit mist, wet impact decal',
    'gameplay':'Existing swept collision, timing, range, damage and poison unchanged',
    'status':'Authored and compiled; no gameplay or visual testing'
}, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('VENOM_LIQUID_AUTHORING_COMPLETE')
