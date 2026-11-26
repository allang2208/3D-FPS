"""Save only the hills map after retiring its fixed daylight study actors."""
from pathlib import Path
import json
import sys
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/HillsNightRepair20261114'
sys.path.insert(0, str(ROOT/'Tools/Weather'))
from hills_sky_ownership import configure_hills_sky

if not u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_TemperateHills_Initial'):
    raise RuntimeError('Cannot load hills map')
sky, retired = configure_hills_sky()
samples = []
for units in (1200., 0., 900.):
    sky.set_editor_property('Time Of Day', units)
    sample = {'time_of_day': sky.get_editor_property('Time Of Day'), 'lights': []}
    for component in sky.get_components_by_class(u.DirectionalLightComponent):
        sample['lights'].append({'name': component.get_name(),
                                'intensity': component.get_editor_property('intensity'),
                                'visible': component.get_editor_property('visible'),
                                'rotation': str(component.get_world_rotation())})
    for name in ('Cached Night Filter', 'Cached Moon Vector', 'Render Moon'):
        sample[name] = str(sky.get_editor_property(name))
    samples.append(sample)
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
    raise RuntimeError('Hills map save failed')
report = {'map': '/Game/GameMaps/L_TemperateHills_Initial', 'retired': retired,
          'sky_actor': sky.get_name(), 'sky_class': sky.get_class().get_path_name(),
          'moon_enabled': sky.get_editor_property('Render Moon'),
          'moon_light_enabled': sky.get_editor_property('Render Moon Directional Light'),
          'construction_samples': samples,
          'saved': True, 'rendered_gameplay_tested': False}
(OUT/'saved.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HILLS_NIGHT_MAP_SAVED ' + str(OUT/'saved.json'))
