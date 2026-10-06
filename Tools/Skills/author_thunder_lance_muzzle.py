"""Author NS_ThunderLanceMuzzle: directional muzzle-shock burst for the lance.

Clone of the NS_ElectricImpact recipe, but the spray is biased into a forward
cone along local +X. The component spawns the system rotated so +X == aim, so
the radial burst reads as a launch shock, not an omni pom-pom. The oriented
shockwave plate lives in C++ (SM_ThunderLanceIris), not in this system.
"""
import json
import sys
from pathlib import Path
import unreal as u
ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_electric_magic_assets import (
    DEST, empty, sprite, shape_material, save,
    assignments, FLOAT, POSITION, VEC2, COLOR, SEED, SEED2, SEED3)
EAL = u.EditorAssetLibrary


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):
        raise RuntimeError('Preserve unsaved ElectricMagic packages')
    spark = u.load_asset(DEST + '/M_ElectricSpark')
    filament = u.load_asset(DEST + '/M_ElectricFilament')
    if not spark or not filament:
        raise RuntimeError('Run build_electric_magic_assets.py first')
    system = empty('NS_ThunderLanceMuzzle')
    # Tight forward cone: dense fast streaks launched along +X.
    cone = f'normalize(float3(1.35,({SEED2}-.5)*1.1,({SEED3}-.5)*1.1))'
    sprite(system, 'ForwardSparks', filament, burst=26, life=.38,
           position=f'({cone})*Particles.Age*(360+{SEED}*280)',
           size=f'float2(50+{SEED3}*34,10)*(1-Particles.NormalizedAge*.55)',
           color='float4(.62,.82,1,1)', rotation=f'{SEED3}*360')
    # Wide skirt: slower splinters scattered sideways off the muzzle.
    wide = f'normalize(float3(.4+.55*{SEED},({SEED2}-.5)*2.7,({SEED3}-.5)*2.7))'
    sprite(system, 'SideSplinters', filament, burst=12, life=.3,
           position=f'({wide})*Particles.Age*(200+{SEED2}*150)',
           size='float2(36,9)*(1-Particles.NormalizedAge*.6)',
           color='float4(.5,.7,1,.9)', rotation=f'{SEED2}*360')
    # Slow residual sparks drifting outward for the afterglow.
    sprite(system, 'ResidualSparks', spark, burst=16, life=.55,
           position=f'({wide})*Particles.Age*(130+{SEED3}*90)',
           size='float2(3,13)*(1-Particles.NormalizedAge*.6)',
           color='float4(.42,.66,1,.9)', rotation=f'{SEED3}*360')
    # White-hot core flash.
    sprite(system, 'MuzzleCore', spark, burst=1, life=.16,
           size='float2(66,66)*(1-Particles.NormalizedAge*.5)',
           color='float4(.85,.95,1,1)')
    system.set_editor_property('fixed_bounds', u.Box(
        min=u.Vector(-160, -340, -340), max=u.Vector(720, 340, 340)))
    save(system)
    receipt = {'saved': [system.get_path_name()],
               'convention': 'local +X == aim direction; component rotates the burst',
               'source': 'NS_ElectricImpact recipe biased forward; iris plate stays in C++',
               'tested': False}
    folder = ROOT / 'SourceAssets/ThunderLanceRay20261005/Records'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'muzzle_authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('LANCE_MUZZLE_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
