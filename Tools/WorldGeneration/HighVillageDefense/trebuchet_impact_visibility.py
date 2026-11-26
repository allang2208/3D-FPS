"""Apply the impact renderer bindings and local bounds without rebuilding the particle graphs."""
from pathlib import Path
import sys
import json
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'Tools/Skills'))
from build_fireball_assets import API, ref, save, setdata


def configure(system):
    wave = ref(system, 'GroundPressure', renderer=0)
    renderer = json.loads(API.call_method('GetRendererData', (wave,)).get_editor_property('property_values'))
    # The explosion template binds alignment to a shape module removed by the siege recipe.
    # Both axes must use the attributes written by the pressure emitter in surface-local space.
    binding = renderer['SpriteFacingBinding']
    binding['rootName'] = binding['dataSetName'] = 'SpriteAlignment'
    binding['paramMapVariable']['name'] = binding['cachedDisplayName'] = 'Particles.SpriteAlignment'
    setdata('SetRendererData', u.NiagaraExt_RendererData, wave, {
        'FacingMode': 'CustomFacingVector', 'Alignment': 'CustomAlignment', 'SpriteAlignmentBinding': binding})

    # Maximum upgraded radius is 725 cm. Include the corners of rotated dust sprites
    # beyond their centres. These local boxes rotate with the impact surface.
    bounds = {'GroundPressure': (735, -5, 15), 'RadialDust': (880, -250, 350),
              'RisingStoneDust': (310, -215, 480)}
    for emitter, (xy, low, high) in bounds.items():
        box = {'min': {'x': -xy, 'y': -xy, 'z': low}, 'max': {'x': xy, 'y': xy, 'z': high}, 'isValid': True}
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter),
                {'CalculateBoundsMode': 'Fixed', 'FixedBounds': box})
    system.set_editor_property('bFixedBounds', True)
    system.set_editor_property('FixedBounds', u.Box(min=u.Vector(-880,-880,-250), max=u.Vector(880,880,480)))


if __name__ == '__main__':
    path = '/Game/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines/FX/NS_TrebuchetStoneImpact'
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing ' + path)
    configure(system)
    save(system)
