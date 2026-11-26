"""Add three CC0 roof voxel materials (thatch / roof_tile / roof_slate) to the palette.

Textures: Poly Haven CC0 (reed_roof_04 / clay_roof_tiles_02 / roof_slates_02), downloaded and
channel-repacked offline (R=Roughness, G=AO) in Saved/RoofTextures/. Materials are authored with
the slope-projected world-space pipeline (weather wetness + edge wear + normal-map detail), so
the roofs match wood/stone exactly. The slope sign and rise are derived from the vertex normal,
so +X/-X/+Y/-Y pitches and both 45°/26.57° rises use the same material. Palette entries carry
their own physics via bOverridePhysics (castle precedent); UVoxelBuildPalette::Physical() is
untouched. Append-only and idempotent.

Usage (editor ideally closed; palette is the only shared asset - reload it in a live editor):
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/add_voxel_roofs_20261014.py -nullrhi -unattended
"""

import unreal as u
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
SRC = ROOT / 'Saved/RoofTextures'
DEST = '/Game/Building/Voxels/Rounded'
TEX_DEST = DEST + '/Textures'
PALETTE = DEST + '/DA_VoxelBuildPalette.DA_VoxelBuildPalette'
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

# kind -> (display name, texture prefix, edge wear, normal strength, physics tuple)
KINDS = {
    'thatch':    ('茅草顶', 'Thatch',    .07, .60, (90.,  500000., 110000.,  90000., 120.,  5.)),
    'roof_tile': ('陶土瓦', 'RoofTile',  .08, .85, (500., 4800000., 420000., 240000., 400., 12.)),
    'roof_slate':('石板瓦', 'RoofSlate', .08, .80, (500., 5200000., 420000., 240000., 450., 12.)),
}

def node(mat, cls): return LIB.create_material_expression(mat, cls)
def wire(source, target, pin, output=''): LIB.connect_material_expressions(source, output, target, pin)
def prop(source, name): LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_' + name))
def scalar(mat, name, value):
    e = node(mat, u.MaterialExpressionScalarParameter)
    e.set_editor_property('parameter_name', name); e.set_editor_property('default_value', value)
    return e
def custom(mat, code, inputs, size):
    e = node(mat, u.MaterialExpressionCustom)
    e.set_editor_property('code', code)
    e.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for name in inputs:
        p = u.CustomInput(); p.set_editor_property('input_name', name); pins.append(p)
    e.set_editor_property('inputs', pins)
    for name, source in inputs.items(): wire(source, e, name)
    return e
def save(obj):
    if not EAL.save_loaded_asset(obj, False): raise RuntimeError('save failed: ' + obj.get_path_name())
    return obj

def import_texture(name, file, srgb, compression):
    path = TEX_DEST + '/' + name
    if not EAL.does_asset_exist(path):
        # Interchange 拒收带 ICC 的源 jpg(clay 瓦件实测),统一走剥 ICC 的 PNG 转存版。
        png = file.with_name(file.stem + '_re.png')
        if png.exists(): file = png
        task = u.AssetImportTask()
        task.set_editor_property('filename', str(file))
        task.set_editor_property('destination_path', TEX_DEST)
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', True)
        TOOLS.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex: raise RuntimeError('import failed: ' + name)
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('compression_settings', compression)
    return save(tex)

EAL.make_directory(TEX_DEST)
surfaces = {}
for kind, (title, prefix, wear, strength, _physics) in KINDS.items():
    tex_bc = import_texture('T_Roof%s_BaseColor' % prefix, SRC / f'{prefix.lower()}_BaseColor.jpg', True,  u.TextureCompressionSettings.TC_DEFAULT)
    tex_n  = import_texture('T_Roof%s_Normal'   % prefix, SRC / f'{prefix.lower()}_Normal.jpg',   False, u.TextureCompressionSettings.TC_NORMALMAP)
    tex_m  = import_texture('T_Roof%s_RHAOM'    % prefix, SRC / f'{prefix.lower()}_RHAOM.png',   False, u.TextureCompressionSettings.TC_MASKS)
    u.log('[roof] textures ready %s' % kind)

    mat_name = 'M_Voxel_Roof' + prefix
    mat = u.load_asset(DEST + '/' + mat_name) if EAL.does_asset_exist(DEST + '/' + mat_name) \
        else TOOLS.create_asset(mat_name, DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('tangent_space_normal', False)
    position = node(mat, u.MaterialExpressionWorldPosition)
    normal = node(mat, u.MaterialExpressionVertexNormalWS)
    # 2026-10-19 修复轮：坡面投影按法线方向展开——s 沿上坡、t 沿檐线，四向坡与 45/26.57°
    # 共用；水平踏面/底面走平面投影，竖直端面走“横×高”，不再让 -X/-Y 坡的 s 变成常数
    # (那是瓦片被拉成一条线、法线贴图失去切向分量的根因)。k 由法线反算，不再依赖参数。
    scale = scalar(mat, 'TextureScaleCm', 40 if kind != 'thatch' else 60)
    uv_slope = custom(mat, """float3 n=normalize(N);
float k=abs(n.z)/max(length(n.xy),1e-3);
bool ax=abs(n.x)>=abs(n.y);
float h=ax?P.x:P.y;
float t=ax?P.y:P.x;
float hs=ax?n.x:n.y;
float sg=hs>=0.0?1.0:-1.0;
float2 uv;
if(abs(n.z)>0.98) uv=float2(h,t);
else if(abs(n.z)<0.20) uv=float2(t,P.z);
else uv=float2((-sg*h+P.z*k)/sqrt(k*k+1.0),t);
return uv/max(Scale,1.0);""", {'P': position, 'N': normal, 'Scale': scale}, 2)
    samples = {}
    for suffix, texture, sampler in [('BaseColor', tex_bc, u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                                     ('Normal', tex_n, u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                                     ('RHAOM', tex_m, u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        t = node(mat, u.MaterialExpressionTextureSample)
        t.set_editor_property('texture', texture); t.set_editor_property('sampler_type', sampler)
        wire(uv_slope, t, 'UVs')
        samples[suffix] = t
    def blended(planes): return planes
    wet = node(mat, u.MaterialExpressionCollectionParameter)
    wet.set_editor_property('collection', u.load_asset('/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather'))
    wet.set_editor_property('parameter_name', 'WeatherWetness')
    edge = custom(mat, 'float3 a=abs(normalize(N)); return saturate((1-max(a.x,max(a.y,a.z)))*3);', {'N': normal}, 1)
    wear_p = scalar(mat, 'EdgeTone', wear)
    color = custom(mat, 'float m=0.97+0.03*sin(P.x*.011+sin(P.y*.007)+P.z*.003); return C*m*(1+Edge*Wear)*lerp(1.0,0.72,saturate(Wet));',
                   {'C': blended(samples['BaseColor']), 'P': position, 'Wet': wet, 'Edge': edge, 'Wear': wear_p}, 3)
    strength_p = scalar(mat, 'NormalStrength', strength)
    detail = custom(mat, '''float3 n=normalize(N);
float k=abs(n.z)/max(length(n.xy),1e-3);
bool ax=abs(n.x)>=abs(n.y);
float hs=ax?n.x:n.y;
float sg=hs>=0.0?1.0:-1.0;
float3 Ds;
if(abs(n.z)>0.98) Ds=float3(1,0,0);
else if(abs(n.z)<0.20) Ds=float3(0,0,1);
else Ds=ax?float3(-sg,0,k):float3(0,-sg,k);
Ds=normalize(Ds);
float3 Dt=ax?float3(0,1,0):float3(1,0,0);
float3 d=(T.x*Ds+T.y*Dt)*Strength;
return normalize(n+d-n*dot(d,n));''',
                    {'T': samples['Normal'], 'N': normal, 'Strength': strength_p}, 3)
    rough = custom(mat, 'return lerp(clamp(M.r+Edge*.04,0.48,0.96),0.3,saturate(Wet));',
                   {'M': blended(samples['RHAOM']), 'Wet': wet, 'Edge': edge}, 1)
    prop(color, 'BASE_COLOR'); prop(detail, 'NORMAL'); prop(rough, 'ROUGHNESS')
    prop(scalar(mat, 'Specular', .3), 'SPECULAR')
    LIB.recompile_material(mat)
    surfaces[kind] = save(mat)
    u.log('[roof] material authored %s' % mat.get_path_name())

stone_mesh = u.load_asset(DEST + '/SM_Voxel20_Stone.SM_Voxel20_Stone')
pal = u.load_asset(PALETTE)
entries = list(pal.get_editor_property('materials'))
# get_editor_property('id') returns unreal.Name objects; without str() the membership
# check below never matches and every rerun appends another copy of the trio
# (bit us 2026-10-15: palette carried 16 entries, 12 of them duplicates).
existing = {str(e.get_editor_property('id')) for e in entries}
for kind, (title, prefix, _w, _s, physics) in KINDS.items():
    if kind in existing:
        u.log('[roof] %s already present' % kind); continue
    entry = u.VoxelBuildMaterial()
    entry.set_editor_property('id', kind)
    entry.set_editor_property('display_name', u.Text(title))
    entry.set_editor_property('surface', surfaces[kind])
    entry.set_editor_property('example_mesh', stone_mesh)
    entry.set_editor_property('override_physics', True)
    ph = u.VoxelPhysicalMaterial()
    ph.set_editor_property('density_kg_m3', physics[0])
    ph.set_editor_property('compression_pa', physics[1])
    ph.set_editor_property('tension_pa', physics[2])
    ph.set_editor_property('shear_pa', physics[3])
    ph.set_editor_property('durability', physics[4])
    ph.set_editor_property('joules_per_damage', physics[5])
    entry.set_editor_property('physics', ph)
    entries.append(entry)
pal.set_editor_property('materials', entries)
save(pal)
for e in pal.get_editor_property('materials'):
    u.log('[roof] palette entry id=%s override=%s' % (e.get_editor_property('id'), e.get_editor_property('override_physics')))
u.log('[roof] DONE total=%d' % len(entries))
