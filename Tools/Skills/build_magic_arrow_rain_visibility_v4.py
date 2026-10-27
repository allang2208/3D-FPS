"""Author stronger Arrow Rain trails and airburst. No gameplay or render run.

Preserves Cone V3 contacts and the shared nocked-arrow flow material. The five
owned packages are saved; smoke/glow, audio and the atlas are read-only inputs.
"""
from pathlib import Path
from datetime import datetime
import json
import shutil
import sys
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets/MagicArrowRain20261026/VisibilityV4'
OUT = ROOT / 'Saved/MagicArrowRain20261026/VisibilityV4'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import build_magic_arrow_rain_assets as base
from build_magic_arrow_rain_airburst_v2 import layer, sprite_material, arrow_tip_material
from build_fireball_assets import API, ref, emitters
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth

DEST, EAL, LIB = base.DEST, u.EditorAssetLibrary, u.MaterialEditingLibrary
VEC4 = '/Script/CoreUObject.Vector4f'
OWNED = ['M_ArrowRainBlastCoreV4', 'M_ArrowRainBlastWaveV4', 'M_ArrowRainTrailV4',
         'M_ArrowRainMetal', 'NS_ArrowRainBurst']


def trail_material():
    mat = base.material('M_ArrowRainTrailV4')
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    # Draw only the front shell: back faces would double the light at glancing angles.
    mat.set_editor_property('two_sided', False)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('output_translucent_velocity', False)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    uv = base.node(mat, u.MaterialExpressionTextureCoordinate)
    time = base.node(mat, u.MaterialExpressionTime)
    normal = base.node(mat, u.MaterialExpressionPixelNormalWS)
    view = base.node(mat, u.MaterialExpressionCameraVectorWS)
    inputs = {'UV': (uv, ''), 'T': (time, ''), 'Normal': (normal, ''), 'View': (view, '')}
    for file, prop, vector in [('TrailOpacity.hlsl', u.MaterialProperty.MP_OPACITY, False),
                               ('TrailColor.hlsl', u.MaterialProperty.MP_EMISSIVE_COLOR, True)]:
        base.output(base.custom(mat, (SRC / file).read_text(encoding='utf8'), inputs, vector), prop)
    base.compile_material(mat)


def upgrade():
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT / 'Content').resolve():
        raise RuntimeError('Author host must share FPSGAME Content')
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(DEST + '/' + name in dirty for name in OWNED):
        raise RuntimeError('Preserve unsaved Arrow Rain visibility assets')
    system = u.load_asset(DEST + '/NS_ArrowRainBurst')
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    smoke = u.load_asset(DEST + '/M_ArrowRainBurstSmokeV2')
    glow = u.load_asset(DEST + '/M_ArrowRainGlow')
    if not system or not source or not smoke or not glow:
        raise RuntimeError('Restore base Arrow Rain and Airburst V2 dependencies first')
    OUT.mkdir(parents=True, exist_ok=True)
    before = SRC / 'Before'
    before.mkdir(parents=True, exist_ok=True)
    for name in OWNED:
        package = ROOT / 'Content/Skills/MagicArrowRain20261026' / (name + '.uasset')
        if package.exists() and not (before / package.name).exists():
            shutil.copy2(package, before / package.name)
    first = len(base.saved)
    core = sprite_material('M_ArrowRainBlastCoreV4', 'CoreMask.hlsl', '3.6', SRC)
    wave = sprite_material('M_ArrowRainBlastWaveV4', 'WaveMask.hlsl', '2.8', SRC)
    trail_material()
    arrow_tip_material(5.8)

    for name in ['AirPressure', 'PressureFlash', 'BurstCoreV2', 'PressureWaveV2',
                 'RollingSmokeV2', 'RadialStreaksV2']:
        if name in emitters(system):
            API.call_method('RemoveEmitter', (ref(system, name),))
    for name in ['Radius', 'Seed', 'Elapsed']:
        user_parameter(system, name, FLOAT)
    a = 'frac((float(Particles.UniqueID)+User.Seed)*.618033989)'
    b = 'frac((float(Particles.UniqueID)+User.Seed)*.414213562)'
    age = '(Particles.Age+User.Elapsed)'
    direction = f'float3(cos({a}*6.28318),sin({a}*6.28318),0)'
    seed = {'Particles.DynamicMaterialParameter': (VEC4, f'float4({a},0,0,0)')}

    def burst_layer(name, material, count, life, values, alignment='Unaligned'):
        layer(system, source, name, material, count, f'max(.01,({life})-User.Elapsed)',
              {**seed, 'Particles.NormalizedAge': (FLOAT, f'saturate({age}/({life}))'), **values}, alignment)

    burst_layer('BurstCoreV4', core, 1, '.24', {
        'Particles.Position': (POSITION, 'float3(0,0,0)'),
        'Particles.SpriteSize': (VEC2, f'float2(1,1)*(210+220*(1-exp(-{age}*36)))'),
        'Particles.Color': (COLOR, f'float4(lerp(float3(.78,1,.85),float3(.07,1,.22),saturate({age}/.055)),.98*(1-{smooth(.065,.24,age)}))')})

    second = '(float(Particles.UniqueID)>.5)'
    delay = f'({second}?.035:0.0)'
    wave_age = f'max(0.0,{age}-{delay})'
    width = f'({second}?User.Radius*1.55:User.Radius*2.35)'
    wave_scale = f'(120+({width}-120)*(1-pow(1-saturate({wave_age}/.28),3)))'
    burst_layer('PressureWaveV4', wave, 2, f'(.32+{delay})', {
        'Particles.Position': (POSITION, 'float3(0,0,10)'),
        'Particles.SpriteSize': (VEC2, f'float2(1,({second}?.88:.52))*{wave_scale}'),
        'Particles.Color': (COLOR, f'float4(.10,1,.25,step({delay},{age})*{smooth(.005,.018,wave_age)}*({second}?.48:.92)*(1-{smooth(.10,.32,wave_age)}))')})

    inner = '(float(Particles.UniqueID)<4.0)'
    radius = f'({inner}?User.Radius*.12:User.Radius*(.41+{b}*.12))'
    alpha = f'({inner}?.90*(1-{smooth(.09,.27,age)}):.84*(1-{smooth(.26,.90,age)}))'
    burst_layer('RollingSmokeV4', smoke, 18, f'.72+{a}*.18', {
        'Particles.Position': (POSITION, f'{direction}*{radius}*(1-exp(-{age}*23))+float3(0,0,({b}-.5)*65+{age}*32)'),
        'Particles.SpriteSize': (VEC2, f'float2(160,125)*(.50+1.0*(1-exp(-{age}*20)))*(.85+{b}*.30)'),
        'Particles.SpriteRotation': (FLOAT, f'({b}-.5)*60+{age}*({a}-.5)*24'),
        'Particles.Color': (COLOR, f'float4(lerp(float3(.26,.53,.32),float3(.16,.26,.19),{smooth(.03,.22,age)}),{alpha}*saturate({age}/.015))')})

    ray = f'normalize({direction}+float3(0,0,({b}-.5)*.90))'
    burst_layer('RadialStreaksV4', glow, 14, f'.22+{b}*.09', {
        'Particles.Position': (POSITION, f'{ray}*(25+330*(1-exp(-{age}*18)))'),
        'Particles.SpriteAlignment': (VEC3, ray),
        'Particles.SpriteSize': (VEC2, f'float2(10,125)*(.60+.40*(1-saturate({age}/.31)))'),
        'Particles.Color': (COLOR, f'float4(.20,1,.35,.95*(1-{smooth(.055,.31,age)}))')}, 'CustomAlignment')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-600,-600,-330), max=u.Vector(600,600,330)))
    EAL.set_metadata_tag(system, 'ArrowRain.AirburstVersion', 'V4: bright core / two fronts / 18 rolling smoke / 14 rays')
    base.finish(system)
    saved = base.saved[first:]
    receipt = {'version': 'VisibilityV4', 'saved_at': datetime.now().isoformat(), 'saved_assets': saved,
               'airburst_particles': {'core': 1, 'wave': 2, 'smoke': 18, 'streaks': 14, 'total': 35},
               'max_airburst_lifetime_seconds': .9, 'falling_trail_radius_cm': [2.6, 3.2],
               'head_glow_during_whole_fall': True, 'new_runtime_components': 0,
               'cone_v3_contacts_changed': False, 'nocked_arrow_flow_changed': False,
               'gameplay_tested': False, 'rendered': False, 'audio_changed': False}
    (OUT / 'asset-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    u.log('MAGIC_ARROW_RAIN_VISIBILITY_V4_SAVED ' + json.dumps(receipt))
    return saved


if __name__ == '__main__':
    upgrade()
