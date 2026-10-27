"""Save the Arrow Rain per-contact green impacts and dust; no gameplay/render run.

One pooled Niagara system receives at most 32 positions, normals and contact
times. Each arrow has one flash, one surface ring, two smoke puffs, three chips.
"""
from pathlib import Path
from datetime import datetime
import json
import shutil
import sys
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets/MagicArrowRain20261026/ConeV3'
OUT = ROOT / 'Saved/MagicArrowRain20261026/ConeV3'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
import build_magic_arrow_rain_assets as base
from build_magic_arrow_rain_airburst_v2 import layer
from build_fireball_assets import API, ref, emitters, setdata, put
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth

DEST = base.DEST
EAL = u.EditorAssetLibrary
VEC4 = '/Script/CoreUObject.Vector4f'


def slot(prefix, index):
    result = f'User.{prefix}31'
    for i in reversed(range(31)):
        result = f'({index}=={i}.0?User.{prefix}{i}:{result})'
    return result


def impact_layer(system, source, name, material, per_arrow, life, kind):
    index = f'floor(float(Particles.UniqueID)/{per_arrow}.0)'
    spawn_values = {
        'Particles.ContactPointV3': (VEC3, slot('Impact', index)),
        'Particles.ContactNormalV3': (VEC3, f'normalize(({slot("ImpactNormal", index)})+float3(0,0,.00001))'),
        'Particles.ContactDelayV3': (FLOAT, slot('ImpactDelay', index)),
        'Particles.ContactRandomAV3': (FLOAT, 'frac((float(Particles.UniqueID)+User.Seed)*.618033989)'),
        'Particles.ContactRandomBV3': (FLOAT, 'frac((float(Particles.UniqueID)+User.Seed)*.414213562)'),
    }
    origin, normal, delay = 'Particles.ContactPointV3', 'Particles.ContactNormalV3', 'Particles.ContactDelayV3'
    raw = f'(Particles.Age+User.Elapsed-({delay}))'
    age = f'max(0.0,{raw})'
    a, b = 'Particles.ContactRandomAV3', 'Particles.ContactRandomBV3'
    life = life.replace('RAND_A', a).replace('RAND_B', b)
    norm = f'saturate({age}/({life}))'
    # Supply the contacted surface's normal and a stable basis, including walls.
    n = normal
    side = f'normalize(cross({n},abs(({n}).z)>.9?float3(1,0,0):float3(0,0,1)))'
    across = f'cross({n},{side})'
    tangent = f'({side}*cos({a}*6.28318)+{across}*sin({a}*6.28318))'
    visible = f'step(0.0,{raw})'
    values = {
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({a},0,0,0)'),
        # Delayed effects must sample their smoke atlas from contact age, not burst age.
        'Particles.NormalizedAge': (FLOAT, norm),
    }
    alignment = 'Unaligned'
    if kind == 'flash':
        position = f'({origin})+{n}*4'
        size = f'float2(46,46)*(1+{age}*4)'
        color = f'float4(.12,1,.32,{visible}*.90*(1-{smooth(.025,.13,age)}))'
    elif kind == 'ring':
        position = f'({origin})+{n}*3'
        size = f'float2(1,1)*(22+64*(1-exp(-{age}*20)))'
        color = f'float4(.08,.94,.24,{visible}*.78*(1-{smooth(.035,.19,age)}))'
        values.update({'Particles.SpriteFacing': (VEC3, n), 'Particles.SpriteAlignment': (VEC3, side)})
        alignment = 'CustomAlignment'
    elif kind == 'smoke':
        position = f'({origin})+{tangent}*(6+{age}*30)+{n}*(5+{age}*25)'
        size = f'float2(54,40)*(.8+{b}*.3)*(1+{age}*.8)'
        color = f'float4(.28,.29,.25,{visible}*.64*saturate({age}/.018)*(1-{smooth(.10,life,age)}))'
        values['Particles.SpriteRotation'] = (FLOAT, f'{b}*360')
    else:
        position = f'({origin})+{tangent}*{age}*(80+{b}*120)+{n}*(4+{age}*(150+{a}*80)-{age}*{age}*350)'
        size = f'float2(3.5,14)*(1-{norm}*.65)'
        color = f'float4(.12,1,.28,{visible}*.85*pow(1-{norm},1.6))'
    values.update({'Particles.Position': (POSITION, position), 'Particles.SpriteSize': (VEC2, size),
                   'Particles.Color': (COLOR, color)})
    lifetime = f'max(.01,({delay})-User.Elapsed+({life}))'
    layer(system, source, name, material, f'floor(clamp(User.Count,0,32)+.5)*{per_arrow}', lifetime, values, alignment, spawn_values)
    put(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=2.0)')
    if kind == 'ring':
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0),
                {'FacingMode': 'CustomFacingVector', 'Alignment': 'CustomAlignment'})


def upgrade():
    if Path(u.Paths.project_content_dir()).resolve() != (ROOT / 'Content').resolve():
        raise RuntimeError('Author host must share FPSGAME Content')
    target = DEST + '/NS_ArrowRainDust'
    if target in {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved Arrow Rain impact package')
    system = u.load_asset(target)
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    glow = u.load_asset(DEST + '/M_ArrowRainGlow')
    ring = u.load_asset(DEST + '/M_ArrowRainPressureWaveV2')
    smoke = u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
    if not all([system, source, glow, ring, smoke]):
        raise RuntimeError('Restore Arrow Rain base, Airburst V2 and shared smoke assets first')
    SRC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    before = SRC / 'Before'
    before.mkdir(exist_ok=True)
    package = ROOT / 'Content/Skills/MagicArrowRain20261026/NS_ArrowRainDust.uasset'
    if package.exists() and not (before / package.name).exists():
        shutil.copy2(package, before / package.name)
    for name in ['GroundImpact', 'EmeraldFragments']:
        if name in emitters(system):
            API.call_method('RemoveEmitter', (ref(system, name),))
    for name, typ in [('Count', FLOAT), ('Seed', FLOAT), ('Elapsed', FLOAT)]:
        user_parameter(system, name, typ)
    for i in range(32):
        for prefix, typ in [('Impact', VEC3), ('ImpactNormal', VEC3), ('ImpactDelay', FLOAT)]:
            user_parameter(system, prefix + str(i), typ)
    impact_layer(system, source, 'ContactFlashV3', glow, 1, '.13', 'flash')
    impact_layer(system, source, 'ContactRingV3', ring, 1, '.19', 'ring')
    impact_layer(system, source, 'ContactDustV3', smoke, 2, '.55+RAND_A*.25', 'smoke')
    impact_layer(system, source, 'ContactChipsV3', glow, 3, '.16+RAND_B*.12', 'chips')
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-650,-650,-350), max=u.Vector(650,650,350)))
    EAL.set_metadata_tag(system, 'ArrowRain.ImpactVersion', 'ConeV3: per-arrow contact time / normal / green flash / ring / dust / chips')
    base.finish(system)
    receipt = {'version': 'ConeV3', 'saved_at': datetime.now().isoformat(), 'saved_assets': [system.get_path_name()],
               'particles_per_arrow': {'flash': 1, 'surface_ring': 1, 'dust': 2, 'chips': 3},
               'normal_arrow_count': 28, 'max_impact_slots': 32, 'peak_normal_particles': 196,
               'longest_contact_fx_seconds': .8, 'new_runtime_components': 0,
               'gameplay_tested': False, 'rendered': False, 'audio_changed': False}
    (OUT / 'asset-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    u.log('MAGIC_ARROW_RAIN_CONE_V3_SAVED ' + json.dumps(receipt))
    return receipt['saved_assets']


if __name__ == '__main__':
    upgrade()
