"""Author the village trebuchet's neutral stone impact in the siege FX package."""
from pathlib import Path
import sys
import unreal as u

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / 'Tools/Skills'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from trebuchet_impact_visibility import configure
from build_fireball_assets import API, emitters, ref, save, setdata
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter
from build_fireball_slow_burn import smooth
from build_magic_arrow_rain_airburst_v2 import layer, VEC4

folder = '/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/FX'
target = folder + '/NS_TrebuchetStoneImpact'
template = '/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small'
library = u.EditorAssetLibrary
source = u.load_asset(template)
smoke = u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
wave = u.load_asset('/Game/Skills/MagicArrowRain20261026/M_ArrowRainPressureWaveV2')
if not all((source, smoke, wave)):
    raise RuntimeError('Missing explosion template, smoke atlas material or pressure wave')
library.make_directory(folder)
system = u.load_asset(target) if library.does_asset_exist(target) else library.duplicate_asset(template, target)
for emitter in emitters(system):
    API.call_method('RemoveEmitter', (ref(system, emitter),))
for parameter in ('Radius', 'Seed'):
    user_parameter(system, parameter, FLOAT)

a = 'frac((float(Particles.UniqueID)+User.Seed)*.618034)'
b = 'frac((float(Particles.UniqueID)+User.Seed)*.414214)'
age = 'Particles.Age'
life = 'Particles.NormalizedAge'
direction = f'float3(cos({a}*6.283185),sin({a}*6.283185),0)'
def puffs(name, count, duration, travel, height, size, shade):
    layer(system, source, name, smoke, count, duration, {
        'Particles.Position': (POSITION, f'{direction}*({travel})+float3(0,0,{height})'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.SpriteRotation': (FLOAT, f'{b}*360'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4({b},0,0,0)'),
        'Particles.Color': (COLOR, f'float4(({shade}).xxx,.76*saturate({age}/.045)*(1-{smooth(.16, 1., life)}))')
    })

# The low skirt expands along the surface normal's tangent plane; the dark core lifts and disperses.
puffs('RadialDust', 13, f'1.1+{b}*.55',
      f'User.Radius*(.52+{b}*.33)*(1-exp(-{age}*3.6))', f'13+{life}*(25+{b}*55)',
      f'float2(170,105)*(.65+{b}*.50)*(1+{life}*1.1)', f'.30+{b}*.11')
puffs('RisingStoneDust', 7, f'.72+{a}*.64',
      f'(17+{b}*65)*(1-exp(-{age}*4))', f'12+(115+{a}*145)*(1-exp(-{age}*2.0))',
      f'float2(100,145)*(.70+{b}*.46)*(1+{life}*1.45)', f'.15+{b}*.10')

layer(system, source, 'GroundPressure', wave, 1, '.37', {
    'Particles.Position': (POSITION, 'float3(0,0,7)'),
    'Particles.SpriteFacing': (VEC3, 'float3(0,0,1)'),
    'Particles.SpriteAlignment': (VEC3, 'float3(1,0,0)'),
    'Particles.SpriteSize': (VEC2, f'float2(1,1)*(40+(2*User.Radius-40)*(1-pow(1-saturate({age}/.34),2)))'),
    'Particles.Color': (COLOR, f'float4(.37,.37,.37,.79*(1-{smooth(.055, .36, age)}))')
}, 'CustomAlignment')
configure(system)
save(system)
