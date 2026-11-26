"""Author stable-local ground finishes using the exterior RoadUpgrade-R48 RoadMix PBR atlases (zero extra VRAM)."""
import hashlib
from pathlib import Path
import unreal as ue

from stable_actors import ROOT

DEST = ROOT + '/GroundDetailR4'
LOESS_FOLDER = '/Game/ForestPathStudy/VillageRegion/Reference/VillageLoess'
ROAD_MIX = '/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/RoadMix'
WEATHER_MPC = '/Game/Weather/Materials/MPC_FPS_Weather'
SRC = Path(__file__).resolve().parents[3] / 'SourceAssets/HillsVillageStable/SurfaceR4'
MAT = ue.MaterialEditingLibrary
LIB = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()

# World-space non-periodic R48 RoadMix surface shader (reuses T_Stony* 2x2 & T_Tire* 2x1 atlases already resident
# for the exterior village road: FineStony / GravelDirt / DarkMud / GroundRoots + compacted hoof/wheel track wear).
STABLE_ROADMIX_HLSL = r'''
struct FRoadCrop
{
    float3 Hash(float2 key)
    {
        float3 v = frac(key.xyx * float3(.1031, .1030, .0973));
        v += dot(v, v.yxz + 33.33);
        return frac((v.xxy + v.yzz) * v.zyx);
    }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        f = f * f * (3. - 2. * f);
        return lerp(lerp(Hash(i).x, Hash(i + float2(1, 0)).x, f.x),
                    lerp(Hash(i + float2(0, 1)).x, Hash(i + 1.).x, f.x), f.y);
    }
    float2 Project(float2 v, float2 ax, float2 ay)
    {
        return float2(dot(v, ax), dot(v, ay));
    }
};

FRoadCrop crop;
float2 terrain = P.xy * .01;
float2 dx = float2(.01, 0.), dy = float2(0., .01);
#if (PIXELSHADER || COMPUTESHADER) && !RAYHITGROUPSHADER
dx = ddx(terrain);
dy = ddy(terrain);
#endif

const float span = 1984. / 2048.;
const float pitch = 1.24;
float extRelief = (1. - smoothstep(320., 1450., distance(P, Eye))) * .013;
float2 viewXY = clamp(V.xy / max(.42, abs(V.z)), -1.6, 1.6);

// Two-octave domain warp eliminates any regular lattice trace across open horse yards.
float2 warpA = float2(crop.Noise(terrain * .41), crop.Noise(terrain * .36 + 19.37)) - .5;
float2 warpB = float2(crop.Noise(terrain * 1.13 + 7.1), crop.Noise(terrain * 1.04 - 11.7)) - .5;
float2 patchXY = terrain + .68 * warpA + .22 * warpB;
float2 grid = float2(patchXY.x - .57735027 * patchXY.y, 1.15470054 * patchXY.y) / pitch;
float2 cell = floor(grid), f = frac(grid);
bool upper = f.x + f.y > 1.;
float3 bary = upper ? float3(f.x + f.y - 1., 1. - f.y, 1. - f.x) : float3(1. - f.x - f.y, f.x, f.y);
float3 weights = bary * bary * bary;

float gravelW = saturate(Weights.g * .82 + .24);
float mudW = saturate(Weights.b * .78);
float edgeRoots = saturate((1. - Weights.g) * .38 + crop.Noise(terrain * .19 + 4.3) * .25) * .32;

float3 tint = 0., tangent = 0., props = 0.;
float mass = 0.;

[unroll] for (int corner = 0; corner < 3; ++corner)
{
    float w = weights[corner];
    [branch] if (w > .00005)
    {
        float2 key = cell + (corner == 0 ? (upper ? float2(1, 1) : float2(0, 0)) : (corner == 1 ? float2(1, 0) : float2(0, 1)));
        float2 centre = float2(key.x + .5 * key.y, .8660254 * key.y) * pitch;
        float3 seed = crop.Hash(key + 41.17), variant = crop.Hash(key - 79.43);

        // Organic 4-tile Stony/Gravel/Mud/Roots mix matching RoadUpgrade-R48 exterior road body
        float pRoots = edgeRoots * .45;
        float pMud = saturate(mudW * .75 + .14) * .58;
        float pGravel = saturate(gravelW * .95) * .88;
        float pFine = .34 + .22 * gravelW;
        float pick = seed.x * (pRoots + pMud + pGravel + pFine);
        float2 tile = float2(0., 0.);
        float physM = 2.0;
        if (pick < pRoots) { tile = float2(1., 1.); physM = 2.0; }
        else if (pick < pRoots + pMud) { tile = float2(0., 1.); physM = 2.0; }
        else if (pick < pRoots + pMud + pGravel) { tile = float2(1., 0.); physM = 2.0; }
        else { tile = float2(0., 0.); physM = .56; }

        float sn, cs;
        sincos(6.2831853 * variant.y, sn, cs);
        float2 ax = float2(cs, sn), ay = float2(-sn, cs);
        float scale = lerp(.90, 1.10, variant.z) / physM;
        float2 coord = crop.Project(terrain - centre, ax, ay) * scale + seed.yz;
        float2 gx = crop.Project(dx, ax, ay) * scale * span * .5;
        float2 gy = crop.Project(dy, ax, ay) * scale * span * .5;
        float2 uv = (tile + .015625 + frac(coord) * span) * .5;

        float3 a = Texture2DSampleGrad(StonyARH, GetMaterialSharedSampler(StonyARHSampler, Material.Clamp_WorldGroupSettings), uv, gx, gy).rgb;
        uv = (tile + .015625 + frac(coord + crop.Project(viewXY, ax, ay) * scale * extRelief * (a.b - .5)) * span) * .5;
        float3 rgb = Texture2DSampleGrad(StonyColor, GetMaterialSharedSampler(StonyColorSampler, Material.Clamp_WorldGroupSettings), uv, gx, gy).rgb;
        float3 micro = UnpackNormalMap(Texture2DSampleGrad(StonyNormal, GetMaterialSharedSampler(StonyNormalSampler, Material.Clamp_WorldGroupSettings), uv, gx, gy));
        float2 nXY = ax * micro.x + ay * micro.y;

        // Height-contrast weighting lets pebbles, grit and mud ridges pop cleanly
        w *= pow(lerp(.55, 1.55, a.b), 1.35);
        tint += w * rgb;
        tangent += w * float3(nXY, micro.z);
        props += w * a;
        mass += w;
    }
}
float invMass = rcp(max(mass, .00001));
tint *= invMass;
tangent = normalize(tangent);
props *= invMass;

// Subtle trampled cart/hoof track wear from R48 2x1 Tire atlas (breaks uniform open yard center)
float wearNoise = crop.Noise(terrain * .28 + 3.7) * .65 + crop.Noise(terrain * .72 - 5.1) * .35;
float trackMask = saturate((mudW * .72 + (1. - gravelW) * .35) * smoothstep(.24, .78, wearNoise));
[branch] if (trackMask > .03)
{
    float mudTile = step(.52, saturate(mudW + RainWetness * .45));
    float phys = mudTile > .5 ? 2.1 : 2.6;
    float2 ax = float2(.9659, .2588), ay = float2(-.2588, .9659);
    float2 local = crop.Project(terrain, ax, ay) / phys;
    float2 invT = float2(.5, 1.);
    float2 tileT = float2(mudTile, 0.);
    float2 gxT = crop.Project(dx, ax, ay) * (span / phys) * invT;
    float2 gyT = crop.Project(dy, ax, ay) * (span / phys) * invT;
    float2 uvT = (tileT + .015625 + frac(local) * span) * invT;
    float3 ta = Texture2DSampleGrad(TireARH, GetMaterialSharedSampler(TireARHSampler, Material.Clamp_WorldGroupSettings), uvT, gxT, gyT).rgb;
    float3 tc = Texture2DSampleGrad(TireColor, GetMaterialSharedSampler(TireColorSampler, Material.Clamp_WorldGroupSettings), uvT, gxT, gyT).rgb;
    float3 tn = UnpackNormalMap(Texture2DSampleGrad(TireNormal, GetMaterialSharedSampler(TireNormalSampler, Material.Clamp_WorldGroupSettings), uvT, gxT, gyT));
    float2 tnXY = ax * tn.x + ay * tn.y;
    float hEdge = smoothstep(.05, .82, trackMask * .62 + (ta.b - props.b) * .22);
    tint = lerp(tint, tc * lerp(1., .88, trackMask), hEdge);
    tangent = normalize(lerp(tangent, float3(tnXY, tn.z), hEdge));
    props = lerp(props, ta, hEdge);
}

// Macro organic tonal break-up (6-22 m) matching RoadUpgrade-R48
float macroV = crop.Noise(terrain * .09 + 11.4) * .65 + crop.Noise(terrain * .23 - 6.8) * .35;
tint *= lerp(float3(.90, .91, .93), float3(1.07, 1.03, .96), macroV);

// Damp mud hollows & rain puddle micro-sheen (responsive to RainWetness MPC)
float localMoist = saturate(mudW * .58 + RainWetness * (.38 + .35 * mudW));
float dampTint = smoothstep(.18, .80, localMoist);
tint *= lerp(1., .66, dampTint);
float rough = lerp(clamp(props.g, .18, .98), min(props.g, .42), dampTint);
float puddleLevel = saturate(localMoist * 1.05 - .54 + (.45 - props.b) * .68);
float puddle = smoothstep(.12, .44, puddleLevel);
[branch] if (puddle > .002)
{
    tint = lerp(tint, tint * .64, puddle);
    tangent = normalize(lerp(tangent, float3(0., 0., 1.), puddle * .90));
    rough = lerp(rough, lerp(.10, .18, crop.Noise(terrain * 2.1)), puddle);
}

// Blend local hoof/cart micro-imprint relief gently without overpowering stone/pebble normals
float3 imp = normalize(float3(Imprints.xy * .55, max(.35, Imprints.z)));
RoadNormal = normalize(float3(tangent.xy + imp.xy, tangent.z * imp.z));
RoadRoughness = rough;
return tint;
'''


def load(path):
    obj = ue.load_asset(path)
    if not obj:
        raise RuntimeError('Missing ground dependency ' + path)
    return obj


def save(obj):
    if not LIB.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save ' + obj.get_path_name())


def atlas(name, normal=False):
    src = SRC / (name + '.png')
    path = DEST + '/T_' + name
    stamp = hashlib.sha256(src.read_bytes()).hexdigest()
    tex = ue.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex and LIB.get_metadata_tag(tex, 'StableGroundSource') == stamp:
        return tex
    task = ue.AssetImportTask()
    task.filename = str(src)
    task.destination_path = DEST
    task.destination_name = 'T_' + name
    task.automated = True
    task.replace_existing = True
    TOOLS.import_asset_tasks([task])
    tex = load(path)
    tex.srgb = False
    tex.compression_settings = ue.TextureCompressionSettings.TC_NORMALMAP if normal else ue.TextureCompressionSettings.TC_MASKS
    if normal:
        tex.flip_green_channel = False
    tex.address_x = tex.address_y = ue.TextureAddress.TA_CLAMP
    LIB.set_metadata_tag(tex, 'StableGroundSource', stamp)
    save(tex)
    return tex


def _build_roadmix_decal(mat, weights_tex, imprints_tex, entrance_feather=False):
    """Build a DeferredDecal material sampling the exterior RoadUpgrade-R48 RoadMix PBR atlases."""
    MAT.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain', ue.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)

    def expr(cls):
        return MAT.create_material_expression(mat, cls)

    def wire(output, to, pin):
        node, channel = output
        if not MAT.connect_material_expressions(node, channel, to, pin):
            raise RuntimeError('Cannot connect ' + pin + ' on ' + to.get_name())

    def finish(output, prop):
        if not MAT.connect_material_property(*output, prop):
            raise RuntimeError('Cannot connect ground property ' + str(prop))

    uv = expr(ue.MaterialExpressionTextureCoordinate)
    w_sample = expr(ue.MaterialExpressionTextureSample)
    w_sample.set_editor_property('texture', weights_tex)
    wire((uv, ''), w_sample, 'UVs')

    imp_sample = expr(ue.MaterialExpressionTextureSample)
    imp_sample.set_editor_property('texture', imprints_tex)
    wire((uv, ''), imp_sample, 'UVs')

    custom = expr(ue.MaterialExpressionCustom)
    custom.set_editor_property('desc', 'StableRoadMixR51')
    custom.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('code', STABLE_ROADMIX_HLSL)

    in_names = (
        'P', 'V', 'Eye', 'Weights', 'Imprints', 'RainWetness',
        'StonyColor', 'StonyNormal', 'StonyARH',
        'TireColor', 'TireNormal', 'TireARH',
    )
    pins = []
    for name in in_names:
        pin = ue.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)

    outputs = []
    for out_name, kind in (('RoadNormal', 'FLOAT3'), ('RoadRoughness', 'FLOAT1')):
        o = ue.CustomOutput()
        o.set_editor_property('output_name', out_name)
        o.set_editor_property('output_type', getattr(ue.CustomMaterialOutputType, 'CMOT_' + kind))
        outputs.append(o)
    custom.set_editor_property('additional_outputs', outputs)

    wire((expr(ue.MaterialExpressionWorldPosition), ''), custom, 'P')
    wire((expr(ue.MaterialExpressionCameraVectorWS), ''), custom, 'V')
    wire((expr(ue.MaterialExpressionCameraPositionWS), ''), custom, 'Eye')
    wire((w_sample, ''), custom, 'Weights')
    wire((imp_sample, ''), custom, 'Imprints')

    rain = expr(ue.MaterialExpressionCollectionParameter)
    rain.set_editor_property('collection', load(WEATHER_MPC))
    rain.set_editor_property('parameter_name', 'WeatherWetness')
    wire((rain, ''), custom, 'RainWetness')

    tex_specs = (
        ('StonyColor', 'COLOR'), ('StonyNormal', 'NORMAL'), ('StonyARH', 'MASKS'),
        ('TireColor', 'COLOR'), ('TireNormal', 'NORMAL'), ('TireARH', 'MASKS'),
    )
    for tname, sampler in tex_specs:
        tobj = expr(ue.MaterialExpressionTextureObject)
        tobj.set_editor_property('texture', load(ROAD_MIX + '/T_' + tname))
        tobj.set_editor_property('sampler_type', getattr(ue.MaterialSamplerType, 'SAMPLERTYPE_' + sampler))
        wire((tobj, ''), custom, tname)

    finish((custom, ''), ue.MaterialProperty.MP_BASE_COLOR)
    finish((custom, 'RoadNormal'), ue.MaterialProperty.MP_NORMAL)
    finish((custom, 'RoadRoughness'), ue.MaterialProperty.MP_ROUGHNESS)

    if entrance_feather:
        feather = expr(ue.MaterialExpressionCustom)
        feather.set_editor_property('desc', 'Village stable entrance wear')
        feather.set_editor_property('output_type', ue.CustomMaterialOutputType.CMOT_FLOAT1)
        fpins = []
        for fname in ('UV', 'Coverage'):
            p = ue.CustomInput()
            p.set_editor_property('input_name', fname)
            fpins.append(p)
        feather.set_editor_property('inputs', fpins)
        feather.set_editor_property('code', '''float2 metres=float2(27.,3.)+UV*float2(36.,44.);
float along=smoothstep(6.,15.,metres.y+.38*sin(metres.x*1.13)+.24*sin(metres.y*2.9));
float entry=smoothstep(38.,47.,metres.x);
return Coverage*lerp(1.,lerp(.18,1.,along),entry);''')
        wire((uv, ''), feather, 'UV')
        wire((w_sample, 'R'), feather, 'Coverage')
        finish((feather, ''), ue.MaterialProperty.MP_OPACITY)
    else:
        finish((w_sample, 'R'), ue.MaterialProperty.MP_OPACITY)

    MAT.layout_material_expressions(mat)
    errors = MAT.recompile_material(mat)
    if errors:
        raise RuntimeError(mat.get_name() + ': ' + '\n'.join(errors))
    save(mat)


def material(name, weights, impressions, interior, extent_cm=(3600., 4400.)):
    path = DEST + '/' + name
    mat = (load(path) if LIB.does_asset_exist(path) else
           TOOLS.create_asset(name, DEST, ue.Material, ue.MaterialFactoryNew()))
    if not interior:
        _build_roadmix_decal(mat, weights, impressions, entrance_feather=False)
        return mat

    MAT.delete_all_material_expressions(mat)
    MAT.set_base_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)

    def expr(cls):
        return MAT.create_material_expression(mat, cls)

    def wire(output, to, pin):
        node, channel = output
        if not MAT.connect_material_expressions(node, channel, to, pin):
            raise RuntimeError('Cannot connect ' + pin + ' on ' + to.get_name())

    def finish(output, prop):
        if not MAT.connect_material_property(*output, prop):
            raise RuntimeError('Cannot connect ground property ' + str(prop))

    def constant(v):
        n = expr(ue.MaterialExpressionConstant)
        n.set_editor_property('r', v)
        return n, ''

    def pair(a, b):
        n = expr(ue.MaterialExpressionConstant2Vector)
        n.set_editor_property('r', a)
        n.set_editor_property('g', b)
        return n, ''

    def op(cls, a, b):
        n = expr(cls)
        wire(a, n, 'A')
        wire(b, n, 'B')
        return n, ''

    def lerp(a, b, alpha):
        n = expr(ue.MaterialExpressionLinearInterpolate)
        wire(a, n, 'A')
        wire(b, n, 'B')
        wire(alpha, n, 'Alpha')
        return n, ''

    def sample(texture, uv_in):
        n = expr(ue.MaterialExpressionTextureSample)
        n.set_editor_property('texture', texture)
        wire(uv_in, n, 'UVs')
        return n

    uv = expr(ue.MaterialExpressionTextureCoordinate), ''
    mul = ue.MaterialExpressionMultiply
    # PackedFloor's imported UV0 is (local X/180, 1-local Y/180).
    # Its one placed instance is centred on village (4400,3950) cm.
    uv = op(ue.MaterialExpressionAdd, op(mul, uv, pair(180 / 3600, -180 / 4400)),
            pair(1700 / 3600, (3950 - 300 + 180) / 4400))
    span_x, span_y = extent_cm
    tiled = op(mul, uv, pair(span_x / 145., span_y / 145.))
    stone_uv = op(mul, uv, pair(span_x / 108., span_y / 108.))
    weights_node = sample(weights, uv)
    gravel = (weights_node, 'G')
    wet = (weights_node, 'B')
    earth = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    rock = '/Game/WorldGeneration/TemperateHills/Upland/Textures/T_RockySteppe_'

    def surfaces(es, rs, ch):
        return lerp((sample(load(earth + es), tiled), ch),
                    (sample(load(rock + rs), stone_uv), ch), gravel)

    base = surfaces('B', 'BaseColor', 'RGB')
    finish(op(mul, base, lerp(constant(1), constant(.66), wet)), ue.MaterialProperty.MP_BASE_COLOR)
    finish(lerp(surfaces('ORM', 'ARH', 'G'), constant(.47), wet), ue.MaterialProperty.MP_ROUGHNESS)
    surface_normal = surfaces('N', 'Normal', 'RGB')
    relief = (sample(impressions, uv), 'RGB')
    combine = expr(ue.MaterialExpressionMaterialFunctionCall)
    combine.set_editor_property('material_function', load('/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals'))
    pins = MAT.get_material_expression_input_names(combine)
    wire(surface_normal, combine, pins[0])
    wire(relief, combine, pins[1])
    normal = (combine, '')
    sign = expr(ue.MaterialExpressionConstant3Vector)
    sign.set_editor_property('constant', ue.LinearColor(1, -1, 1, 1))
    normal = op(mul, normal, (sign, ''))
    finish(normal, ue.MaterialProperty.MP_NORMAL)
    MAT.layout_material_expressions(mat)
    errors = MAT.recompile_material(mat)
    if errors:
        raise RuntimeError(mat.get_name() + ': ' + '\n'.join(errors))
    save(mat)
    return mat


def author():
    LIB.make_directory(DEST)
    weights = atlas('StableGroundWeights')
    relief = atlas('StableImprintsDX', True)
    material('M_StableYardSoil', weights, relief, False)
    material('M_StableStallFloor', weights, relief, True)
    # Also rebuild the live ForestVillage runtime decal variant (VillageStableEntryWear) with R48 RoadMix + entrance feather!
    loess_path = LOESS_FOLDER + '/M_StableYardLoessBlend'
    if LIB.does_asset_exist(loess_path):
        loess_mat = load(loess_path)
        _build_roadmix_decal(loess_mat, weights, relief, entrance_feather=True)


def author_west_paddock():
    LIB.make_directory(DEST)
    weights = atlas('StableWestPaddockWeights')
    relief = atlas('StableWestPaddockImprintsDX', True)
    material('M_StableWestPaddockSoil', weights, relief, False, extent_cm=(2300., 1500.))
