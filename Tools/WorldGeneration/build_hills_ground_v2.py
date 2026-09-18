"""Rebuild the temperate-hills ground material as a layered, height-blended surface.

Supersedes the three-layer graph authored by build_temperate_hills.py and, with it,
the river-bank graph authored by build_pebble_shore.py.

Two materials are rebuilt in place so their asset paths (and therefore the soft
reference on DA_TemperateHillsStreaming) never change:
  * M_TemperateGround   - the layered hill ground.
  * M_PebbleShoreGround - the same hill ground with the river bank/pebble blend on
                          top, which is the material the data asset points at.

What the new base graph adds over the flat three-layer version:
  1. Four ground families (grass, soil, gravel, dry crust) projected at different
     world scales, so the surface stops reading as one tiled sheet.
  2. Height-map weighted blending: every family's own height map drives the
     transition, so layers interlock along their relief instead of cross-fading.
  3. Bounded, distance-faded parallax occlusion over the soil and gravel height
     fields, which is what gives the near ground its depth.
  4. Whiteout normal blending plus a distance-faded fine-grain detail pass.
  5. Multi-scale macro variation on albedo and roughness against visible tiling.
  6. Cavity ambient occlusion derived from the same height maps.
  7. The existing weather-driven `Wetness` scalar and the per-vertex damp channel
     (vertex colour G) darken, smooth and flatten the relief.

Run headless against an editor build; no map is opened and no gameplay is launched.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
PEBBLE_DIR = BASE + '/PebbleShore'
OUT = ROOT / 'Saved/GroundMaterialUpgrade20260918'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / ('BeforeAuthoring-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
REPORT = {'scope': 'Ground material authoring only; no gameplay, map or visual test',
          'sources': [], 'saved': [], 'backups': [], 'materials': {}}

GROUND = BASE + '/M_TemperateGround'
PEBBLE = PEBBLE_DIR + '/M_PebbleShoreGround'

# Value noise, written out inline. The material compiler wraps a Custom node's code
# in a function body, so the node cannot declare helper functions - every use has to
# be spelled out. The hash constants match the previous ground graph so the patch
# layout of the existing world does not change.
NOISE_TEMPLATE = (
    'float2 q{t}=P.xy*{f}+float2({ox},{oy});'
    'float2 i{t}=floor(q{t}),f{t}=frac(q{t});f{t}=f{t}*f{t}*(3-2*f{t});\n'
    'float4 h{t}=frac(sin(float4(dot(i{t},float2(127.1,311.7)),'
    'dot(i{t}+float2(1,0),float2(127.1,311.7)),'
    'dot(i{t}+float2(0,1),float2(127.1,311.7)),'
    'dot(i{t}+float2(1,1),float2(127.1,311.7))))*43758.5453);\n'
    'float {out}=lerp(lerp(h{t}.x,h{t}.y,f{t}.x),lerp(h{t}.z,h{t}.w,f{t}.x),f{t}.y);\n')


def noise(tag, freq, ox=0.0, oy=0.0):
    """Inline value noise. Returns (hlsl, variable name)."""
    out = 'n' + tag
    return NOISE_TEMPLATE.format(t=tag, f=freq, ox=ox, oy=oy, out=out), out

# Grass covers flat, damp, grazed ground; soil is the default disturbed dirt; gravel
# takes the steeper slopes; the dry crust paints the pale stony flats that the
# reference look is built around. Only the dry crust ships without a height map, so
# it blends on a fixed mid height and never drives the parallax.
LAYERS = [
    {'name': 'Grass', 'tiling': 5.6, 'family': 'GroundGrassTilingM', 'offset': (0.17, 0.43),
     'albedo': '/Game/PN_GrassLibrary/Textures/LandscapeTextures/ground_I_albedo',
     'normal': '/Game/PN_GrassLibrary/Textures/LandscapeTextures/ground_I_normal',
     'height': '/Game/PN_GrassLibrary/Textures/LandscapeTextures/ground_I_height',
     'rough': None},
    {'name': 'Soil', 'tiling': 3.0, 'family': 'GroundSoilTilingM', 'offset': (0.61, 0.08),
     'albedo': '/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Albedo',
     'normal': '/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Normal',
     'height': '/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Height',
     'rough': '/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_RHAOM'},
    {'name': 'Gravel', 'tiling': 2.1, 'family': 'GroundGravelTilingM', 'offset': (0.33, 0.77),
     'albedo': '/Game/UnrealNormandy/Textures/T_LC_MossyGravel_00A_Albedo',
     'normal': '/Game/UnrealNormandy/Textures/T_LC_MossyGravel_00A_Normal',
     'height': '/Game/UnrealNormandy/Textures/T_LC_MossyGravel_00A_Height',
     'rough': '/Game/UnrealNormandy/Textures/T_LC_MossyGravel_00A_RHAOM'},
    {'name': 'Dry', 'tiling': 7.5, 'family': 'GroundDryTilingM', 'offset': (0.83, 0.29),
     'albedo': '/Game/UnrealNormandy/Textures/T_LC_GroundDry_00A_Albedo',
     'normal': '/Game/UnrealNormandy/Textures/T_LC_GroundDry_00A_Normal',
     'height': None,
     'rough': '/Game/UnrealNormandy/Textures/T_LC_GroundDry_00A_RHAOM'},
]


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing ground source: ' + path)
    if path not in REPORT['sources']:
        REPORT['sources'].append(path)
    return obj


def backup(path):
    source = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    if not source.exists():
        return None
    target = BACKUP / source.relative_to(ROOT / 'Content')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    REPORT['backups'].append(str(target))
    return target


def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save ' + obj.get_path_name())
    if obj.get_path_name() not in REPORT['saved']:
        REPORT['saved'].append(obj.get_path_name())
    return obj


def node(mat, cls):
    return LIB.create_material_expression(mat, cls)


def wire(source, target, pin, out=''):
    if not LIB.connect_material_expressions(source, out, target, pin):
        raise RuntimeError('Connection failed: %s.%s -> %s' % (source.get_class().get_name(), out, pin))


def prop(source, name):
    if not LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Material output failed: ' + name)


def custom(mat, code, inputs, width=3, desc=None):
    expr = node(mat, u.MaterialExpressionCustom)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    if desc:
        expr.set_editor_property('desc', desc)
    for name, source in inputs.items():
        wire(source, expr, name)
    return expr


def scalar(mat, name, value, desc=None):
    expr = node(mat, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', value)
    if desc:
        expr.set_editor_property('desc', desc)
    return expr


def sampler_enum(name):
    """MaterialSamplerType members are exposed upper case."""
    member = getattr(u.MaterialSamplerType, name.upper(), None)
    if member is None:
        raise RuntimeError('Unknown MaterialSamplerType member: ' + name)
    return member


def required_sampler_type(texture):
    """The sampler type UE demands for this texture.

    This mirrors UTexture::GetMaterialType(): compression settings decide first, sRGB
    only distinguishes Color from LinearColor. A mismatch is a material compile ERROR
    ("Sampler type is X, should be Y"), and the in-game symptom is the default
    checkerboard material over the whole terrain - not a warning. The mask-compressed
    height and RHAOM scans in this project are the ones a naive sRGB-only guess gets
    wrong: they are linear but must be sampled as Masks.
    """
    key = str(texture.get_editor_property('compression_settings')).split('.')[-1].split(':')[0].strip().upper()
    mapped = {
        'TC_ALPHA': 'SAMPLERTYPE_ALPHA',
        'TC_GRAYSCALE': 'SAMPLERTYPE_GRAYSCALE',
        'TC_NORMALMAP': 'SAMPLERTYPE_NORMAL',
        'TC_MASKS': 'SAMPLERTYPE_MASKS',
        'TC_DISPLACEMENTMAP': 'SAMPLERTYPE_DISPLACEMENT',
        'TC_DISTANCEFIELDFONT': 'SAMPLERTYPE_DISTANCEFIELD_FONT',
        'TC_HDR': 'SAMPLERTYPE_LINEAR_COLOR',
        'TC_HDR_COMPRESSED': 'SAMPLERTYPE_LINEAR_COLOR',
    }.get(key)
    if mapped and hasattr(u.MaterialSamplerType, mapped):
        return sampler_enum(mapped)
    return sampler_enum('SAMPLERTYPE_COLOR' if texture.get_editor_property('srgb') else 'SAMPLERTYPE_LINEAR_COLOR')


def sample(mat, texture, uv):
    expr = node(mat, u.MaterialExpressionTextureSample)
    expr.set_editor_property('texture', texture)
    expr.set_editor_property('sampler_type', required_sampler_type(texture))
    expr.set_editor_property('sampler_source', u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    wire(uv, expr, 'UVs')
    return expr


def height_object(mat, texture):
    """Explicit texture object for the parallax loop, which samples inside the loop."""
    expr = node(mat, u.MaterialExpressionTextureObject)
    expr.set_editor_property('texture', texture)
    expr.set_editor_property('sampler_type', required_sampler_type(texture))
    return expr


def build_base(mat):
    """Layered hill ground. Returns the four nodes to feed the material outputs."""
    world = node(mat, u.MaterialExpressionWorldPosition)
    normal_ws = node(mat, u.MaterialExpressionVertexNormalWS)
    vcol = node(mat, u.MaterialExpressionVertexColor)
    camera = node(mat, u.MaterialExpressionCameraPositionWS)
    view = node(mat, u.MaterialExpressionCameraVectorWS)
    wetness = scalar(mat, 'Wetness', 0.0, desc='Weather- and time-of-day driven surface wetness.')

    # ---- family weights: slope plus two patch fields, all in world space ----
    patch, patch_v = noise('a', 0.0000405)
    patch2, patch2_v = noise('b', 0.000183, 17.3, -9.1)
    weights = custom(mat, patch + patch2 + '''
float damp=saturate(max(Wet,M.g));
float slope=saturate(1.0-N.z);
float gravel=saturate(smoothstep(0.17,0.46,slope)*1.35+(%s-0.62)*1.2);
float grass=saturate((1.0-smoothstep(0.05,0.30,slope))*(0.30+%s*1.30)*(0.40+damp*1.30))*(1.0-gravel*0.85);
float dry=saturate((1.0-smoothstep(0.08,0.34,slope))*(1.25-%s)*(1.35-damp))*(1.0-gravel*0.85);
float soil=saturate(1.0-grass-dry-gravel)+0.10;
return float4(grass,soil,gravel,dry)/max(grass+soil+gravel+dry,0.0001);
''' % (patch2_v, patch_v, patch_v),
                  {'P': world, 'N': normal_ws, 'M': vcol, 'Wet': wetness}, 4, desc='GroundFamilyWeights')

    # ---- projection: parallax the shared base UV, then rescale per family ----
    base_tiling = scalar(mat, 'GroundBaseTilingM', 3.4,
                         desc='World metres of one texture tile for the shared projection.')
    relief_fade = scalar(mat, 'GroundReliefFadeM', 7.0,
                         desc='Relief is at full strength inside this distance and gone by 2.3x.')
    wet_factor = custom(mat, 'return saturate(max(Wet,M.g));', {'Wet': wetness, 'M': vcol}, 1)
    cam_dist = custom(mat, 'return length(Camera-P);', {'Camera': camera, 'P': world}, 1)
    relief_fade_curve = custom(mat, 'return 1.0-smoothstep(F*100.0,F*230.0,D);',
                               {'F': relief_fade, 'D': cam_dist}, 1)
    detail_fade = scalar(mat, 'GroundDetailFadeM', 10.0,
                         desc='Fine grain detail is at full strength inside this distance.')
    detail_fade_curve = custom(mat, 'return 1.0-smoothstep(F*100.0,F*230.0,D);',
                               {'F': detail_fade, 'D': cam_dist}, 1)
    # The river bank runs its own relief march on the same surface; suppress the hill
    # march there (vertex colour R is the bank mask) so the two never stack.
    relief_amount = custom(mat,
                           'return Depth*Fade*smoothstep(0.15,0.42,V.z)*saturate(1.0-M.r)*(1.0-0.65*WetF);',
                           {'Depth': scalar(mat, 'GroundReliefDepthCm', 9.0,
                                            desc='Parallax depth in cm. 0 disables the relief march.'),
                            'Fade': relief_fade_curve, 'V': view, 'M': vcol, 'WetF': wet_factor}, 1)
    weights_gr = custom(mat, 'return W.z/max(W.y+W.z,0.0001);', {'W': weights}, 1,
                        desc='Parallax composite blend between the soil and gravel heights')
    uv_base = custom(mat, '''
float2 base=P.xy/(B*100.0);
float2 gx=ddx(base),gy=ddy(base);
float relief=Amount/(B*100.0);
if(relief<0.0001) return base;
float2 travel=V.xy/max(V.z,0.15)*relief;
int steps=min((int)lerp(Steps,max(4.0,Steps*0.55),saturate(V.z)),24);
float dt=1.0/steps,ray=0.0,previousRay=0.0,previousGap=1.0,gap=1.0;
[loop] for(int i=0;i<=24;++i)
{
    float2 at=base-travel*ray;
    float a=Texture2DSampleGrad(H0,H0Sampler,at,gx,gy).r;
    float b=Texture2DSampleGrad(H1,H1Sampler,at,gx,gy).r;
    gap=1.0-lerp(a,b,Blend)-ray;
    if(gap<=0.0||i==steps) break;
    previousRay=ray;previousGap=gap;ray+=dt;
}
float hit=lerp(previousRay,ray,saturate(previousGap/max(previousGap-gap,0.0001)));
return base-travel*hit;
''', {'P': world, 'V': view, 'B': base_tiling, 'Amount': relief_amount,
      'Steps': scalar(mat, 'GroundReliefSteps', 10.0, desc='Maximum relief march steps (capped at 24).'),
      'Blend': weights_gr,
      'H0': height_object(mat, load(LAYERS[1]['height'])),
      'H1': height_object(mat, load(LAYERS[2]['height']))}, 2, desc='GroundParallaxUV')
    uv_world = custom(mat, 'return U*(B*100.0);', {'U': uv_base, 'B': base_tiling}, 2)

    layer_uv = []
    for layer in LAYERS:
        ox, oy = layer['offset']
        layer_uv.append(custom(mat, 'return P.xy/(T*100.0)+float2(%.3f,%.3f);' % (ox, oy),
                               {'P': uv_world, 'T': scalar(mat, layer['family'], layer['tiling'])}, 2))

    albedo = [sample(mat, load(layer['albedo']), layer_uv[i]) for i, layer in enumerate(LAYERS)]
    normals = [sample(mat, load(layer['normal']), layer_uv[i]) for i, layer in enumerate(LAYERS)]
    heights = [sample(mat, load(layer['height']), layer_uv[i]) for i, layer in enumerate(LAYERS[:3])]
    roughness = [sample(mat, load(layer['rough']), layer_uv[i]) if layer['rough']
                 else scalar(mat, 'GroundGrassRoughness', 0.86) for i, layer in enumerate(LAYERS)]

    # ---- height-weighted blend: a family wins where its own surface is proud ----
    blend_weights = custom(mat, '''
float4 boost=saturate((float4(hG.r,hS.r,hR.r,0.5)-Bias)*Contrast+1.0);
float4 w=W*boost;
return w/max(dot(w,float4(1,1,1,1)),0.0001);
''', {'W': weights, 'hG': heights[0], 'hS': heights[1], 'hR': heights[2],
      'Bias': scalar(mat, 'GroundHeightBias', 0.34, desc='Height at which a family stops gaining ground.'),
      'Contrast': scalar(mat, 'GroundHeightContrast', 2.4, desc='Sharpness of the height-based transition.')},
        4, desc='GroundHeightBlendedWeights')

    macro_a, macro_a_v = noise('a', 0.000052)
    macro_b, macro_b_v = noise('b', 0.00021, 31.7, 5.9)
    macro = custom(mat, macro_a + macro_b + 'return Macro*((%s-0.5)+0.55*(%s-0.5));' % (macro_a_v, macro_b_v),
                   {'P': world, 'Macro': scalar(mat, 'GroundMacroStrength', 0.10,
                                               desc='Large-scale albedo and roughness variation against visible tiling.')},
                   1)

    # ---- fine grain: one extra sample of the gravel family at close range ----
    detail_strength = scalar(mat, 'GroundDetailStrength', 0.5, desc='Fine grain strength in the near field.')
    detail_uv = custom(mat, 'return P.xy/(T*100.0)+float2(0.137,0.911);',
                       {'P': uv_world, 'T': scalar(mat, 'GroundDetailTilingM', 0.9,
                                                   desc='World metres of one fine-grain tile.')}, 2)
    detail_albedo = sample(mat, load(LAYERS[2]['albedo']), detail_uv)
    detail_normal = sample(mat, load(LAYERS[2]['normal']), detail_uv)

    color = custom(mat, '''
float3 a=A.rgb*W.x+B.rgb*W.y+C.rgb*W.z+D.rgb*W.w;
float grain=dot(DT.rgb,float3(0.30,0.59,0.11));
return a*(1.0+Macro)*lerp(1.0,0.78+0.44*grain,saturate(DS*Fade));
''', {'A': albedo[0], 'B': albedo[1], 'C': albedo[2], 'D': albedo[3], 'W': blend_weights,
      'Macro': macro, 'DT': detail_albedo, 'DS': detail_strength, 'Fade': detail_fade_curve},
        3, desc='GroundBaseColor')

    normal = custom(mat, '''
float3 n=normalize(float3(0.0,0.0,1.0));
n=normalize(float3(n.xy+A.rgb.xy*W.x,n.z*A.rgb.z));
n=normalize(float3(n.xy+B.rgb.xy*W.y,n.z*B.rgb.z));
n=normalize(float3(n.xy+C.rgb.xy*W.z,n.z*C.rgb.z));
n=normalize(float3(n.xy+D.rgb.xy*W.w,n.z*D.rgb.z));
n=normalize(float3(n.xy+DN.rgb.xy*saturate(DS*Fade)*0.6,n.z*DN.rgb.z));
return normalize(float3(n.xy*Str,n.z));
''', {'A': normals[0], 'B': normals[1], 'C': normals[2], 'D': normals[3], 'W': blend_weights,
      'DN': detail_normal, 'DS': detail_strength, 'Fade': detail_fade_curve,
      'Str': scalar(mat, 'GroundNormalStrength', 1.15)}, 3, desc='GroundNormal')

    rough = custom(mat, '''
float r=R.r*W.y+G.r*W.z+Y.r*W.w+Grass*W.x;
return lerp(clamp(r*(1.0+Macro*1.4),0.30,0.97),WetRough,WetF);
''', {'R': roughness[1], 'G': roughness[2], 'Y': roughness[3], 'Grass': roughness[0],
      'W': blend_weights, 'Macro': macro,
      'WetRough': scalar(mat, 'GroundWetRoughness', 0.26), 'WetF': wet_factor}, 1,
        desc='GroundRoughness')

    ao = custom(mat, '''
float cavity=(0.60+0.40*hG.r)*W.x+(0.55+0.45*hS.r)*W.y+(0.50+0.50*hR.r)*W.z+0.92*W.w;
return lerp(1.0,cavity,Strength);
''', {'hG': heights[0], 'hS': heights[1], 'hR': heights[2], 'W': blend_weights,
      'Strength': scalar(mat, 'GroundAOStrength', 0.65,
                         desc='Crevice darkening from the family height maps.')}, 1,
        desc='GroundAmbientOcclusion')

    return {'BASE_COLOR': color, 'NORMAL': normal, 'ROUGHNESS': rough, 'AMBIENT_OCCLUSION': ao,
            'shared': {'world': world, 'view': view, 'camera': camera, 'vcol': vcol, 'wetness': wetness}}


def build_river_bank(mat, hill):
    """Blend the river bank and pebble scans over the hill ground.

    Ported from build_pebble_shore.py: same two scans, same bounded relief march,
    same vertex-colour contract (R bank, G damp, B pebble bars) written by
    TemperateHillsStreaming.cpp, but sourced from the new hill outputs.
    """
    maps = [{'BaseColor': load(BASE + '/Rivers/T_RiverShore_BaseColor'),
             'Normal': load(BASE + '/Rivers/T_RiverShore_Normal'),
             'Roughness': load(BASE + '/Rivers/T_RiverShore_Roughness'),
             'Displacement': load(PEBBLE_DIR + '/T_RiverShore_Displacement'),
             'AO': load(PEBBLE_DIR + '/T_RiverShore_AO')},
            {'BaseColor': load(BASE + '/Rivers/T_RiverPebbles_BaseColor'),
             'Normal': load(BASE + '/Rivers/T_RiverPebbles_Normal'),
             'Roughness': load(BASE + '/Rivers/T_RiverPebbles_Roughness'),
             'Displacement': load(PEBBLE_DIR + '/T_RiverPebbles_Displacement'),
             'AO': load(PEBBLE_DIR + '/T_RiverPebbles_AO')}]

    world = hill['shared']['world']
    view = hill['shared']['view']
    camera = hill['shared']['camera']
    mask = hill['shared']['vcol']
    wet = hill['shared']['wetness']
    blend = custom(mat, 'return lerp(.88,.12,saturate(M.b*1.2));', {'M': mask}, 1)
    height_objects = [height_object(mat, texset['Displacement']) for texset in maps]

    uv = custom(mat, '''
float2 base=P.xy/200.0;
float2 gx=ddx(base), gy=ddy(base);
float amount=saturate(M.r)*saturate(1-smoothstep(900,1800,length(Camera-P)))*smoothstep(.08,.28,V.z);
float relief=HeightCm*amount;
if(relief<.001) return base;
float2 travel=V.xy/max(V.z,.12)*relief/200.0;
int steps=(int)lerp(20.0,8.0,saturate(V.z));
float dt=1.0/steps;
float ray=0, previousRay=0, previousGap=1, gap=1;
[loop] for(int i=0;i<=20;++i)
{
    float2 at=base-travel*ray;
    float a=Texture2DSampleGrad(H0,H0Sampler,at,gx,gy).r;
    float b=Texture2DSampleGrad(H1,H1Sampler,at,gx,gy).r;
    float weight=saturate((Blend+(b-a)*.28-.43)/.14);
    gap=1-lerp(a,b,weight)-ray;
    if(gap<=0 || i==steps) break;
    previousRay=ray;previousGap=gap;ray+=dt;
}
float hit=lerp(previousRay,ray,saturate(previousGap/max(previousGap-gap,.0001)));
return base-travel*hit;
''', {'P': world, 'Camera': camera, 'V': view, 'M': mask, 'Blend': blend,
      'HeightCm': scalar(mat, 'PebbleReliefDepthCm', 5.0),
      'H0': height_objects[0], 'H1': height_objects[1]}, 2)

    samples = [{kind: sample(mat, texture, uv) for kind, texture in texset.items()}
               for texset in maps]
    height_blend = custom(mat, 'return saturate((Blend+(B.r-A.r)*.28-.43)/.14);',
                          {'Blend': blend, 'A': samples[0]['Displacement'], 'B': samples[1]['Displacement']}, 1)
    bank_ao = custom(mat, 'return clamp(lerp(A.r,B.r,T),.30,1);',
                     {'A': samples[0]['AO'], 'B': samples[1]['AO'], 'T': height_blend}, 1)
    bank_color = custom(mat, '''
float damp=max(M.g,saturate(Wet));
float macro=.95+.05*sin(P.x*.00073+sin(P.y*.00053));
return lerp(A,B,T)*macro*lerp(1.0,.62,damp)*lerp(.88,1.0,AO);
''', {'A': samples[0]['BaseColor'], 'B': samples[1]['BaseColor'], 'T': height_blend,
      'M': mask, 'Wet': wet, 'P': world, 'AO': bank_ao}, 3)
    bank_normal = custom(mat, 'float3 n=normalize(lerp(A,B,T)); return normalize(float3(n.xy*Strength,n.z));',
                         {'A': samples[0]['Normal'], 'B': samples[1]['Normal'], 'T': height_blend,
                          'Strength': scalar(mat, 'PebbleNormalStrength', 1.10)}, 3)
    bank_rough = custom(mat, 'return lerp(clamp(lerp(A.r,B.r,T),.53,.94),.25,max(M.g,saturate(Wet)));',
                        {'A': samples[0]['Roughness'], 'B': samples[1]['Roughness'], 'T': height_blend,
                         'M': mask, 'Wet': wet}, 1)

    return {'BASE_COLOR': custom(mat, 'return lerp(A,B,saturate(M.r));',
                                 {'A': hill['BASE_COLOR'], 'B': bank_color, 'M': mask}, 3,
                                 desc='HillRiverBaseColor'),
            'NORMAL': custom(mat, 'return normalize(lerp(A,B,saturate(M.r)));',
                             {'A': hill['NORMAL'], 'B': bank_normal, 'M': mask}, 3, desc='HillRiverNormal'),
            'ROUGHNESS': custom(mat, 'return lerp(A,B,saturate(M.r));',
                                {'A': hill['ROUGHNESS'], 'B': bank_rough, 'M': mask}, 1,
                                desc='HillRiverRoughness'),
            'AMBIENT_OCCLUSION': custom(mat, 'return lerp(A,B,saturate(M.r));',
                                        {'A': hill['AMBIENT_OCCLUSION'], 'B': bank_ao, 'M': mask}, 1,
                                        desc='HillRiverAmbientOcclusion')}


def rebuild(path, with_bank):
    backup(path)
    mat = load(path)
    before = len(LIB.get_material_expressions(mat) or [])
    LIB.delete_all_material_expressions(mat)
    stale = LIB.get_material_expressions(mat) or []
    if stale and hasattr(LIB, 'delete_material_expression'):
        for expr in list(stale):
            LIB.delete_material_expression(mat, expr)
        stale = LIB.get_material_expressions(mat) or []
    outputs = build_base(mat)
    if with_bank:
        outputs = build_river_bank(mat, outputs)
    for name in ('BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'AMBIENT_OCCLUSION'):
        prop(outputs[name], name)
    LIB.recompile_material(mat)
    save(mat)
    connected = {}
    for name in ('BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'AMBIENT_OCCLUSION'):
        found = LIB.get_material_property_input_node(mat, getattr(u.MaterialProperty, 'MP_' + name))
        connected[name] = [str(found.get_editor_property('desc')), found.get_class().get_name()] if found else None
    REPORT['materials'][path] = {
        'with_river_bank': with_bank,
        'expressions_before': before,
        'stale_after_delete': len(stale),
        'expressions': len(LIB.get_material_expressions(mat) or []),
        'scalars': sorted(str(n) for n in (LIB.get_scalar_parameter_names(mat) or [])),
        'outputs': connected,
    }
    return mat


hill_material = rebuild(GROUND, with_bank=False)
pebble_material = rebuild(PEBBLE, with_bank=True)

assets = load(BASE + '/DA_TemperateHillsStreaming')
current = assets.get_editor_property('ground_material')
if current is None or current.get_path_name().split('.')[0] != PEBBLE:
    backup(BASE + '/DA_TemperateHillsStreaming')
    assets.set_editor_property('ground_material', pebble_material)
    save(assets)
REPORT['ground_material'] = (assets.get_editor_property('ground_material').get_path_name()
                             if assets.get_editor_property('ground_material') else None)

(OUT / 'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('GROUND_UPGRADE_BEGIN')
for line in json.dumps(REPORT, ensure_ascii=False, indent=2).splitlines():
    u.log('GROUND_UPGRADE ' + line)
u.log('GROUND_UPGRADE_END')
u.log('GROUND_UPGRADE_COMPLETE')
print(json.dumps(REPORT['materials'], ensure_ascii=False, indent=2))
