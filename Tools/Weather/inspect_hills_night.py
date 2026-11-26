"""Read the current hills lighting and UDS clock graphs without saving assets."""
import json
import re
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/HillsNightRepair20261114'
OUT.mkdir(parents=True, exist_ok=True)
report = {'map': '/Game/GameMaps/L_TemperateHills_Initial', 'actors': [], 'sky_defaults': {}}

def value(obj, name):
    try:
        v = obj.get_editor_property(name)
        if isinstance(v, (bool, int, float, str)) or v is None:
            return v
        return str(v)
    except Exception as error:
        return {'error': str(error)}

def export(obj, filename):
    task = u.AssetExportTask()
    task.object = obj
    task.filename = str(OUT / filename)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.ObjectExporterT3D()
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Cannot export ' + filename)

world = u.EditorLoadingAndSavingUtils.load_map(report['map'])
if not world:
    raise RuntimeError('Cannot load hills map')
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    relevant = isinstance(actor, (u.DirectionalLight, u.SkyLight, u.SkyAtmosphere,
                                 u.ExponentialHeightFog, u.PostProcessVolume, u.FPSWeatherManager))
    if not relevant and 'Ultra_Dynamic' not in actor.get_class().get_name():
        continue
    row = {'name': actor.get_name(), 'label': actor.get_actor_label(),
           'class': actor.get_class().get_path_name(), 'hidden': value(actor, 'hidden'),
           'rotation': str(actor.get_actor_rotation()), 'components': []}
    for component in actor.get_components_by_class(u.SceneComponent):
        fields = ('visible', 'hidden_in_game')
        if isinstance(component, (u.LightComponent, u.SkyLightComponent)):
            fields += ('intensity', 'affects_world')
        if isinstance(component, u.DirectionalLightComponent):
            fields += ('atmosphere_sun_light', 'atmosphere_sun_light_index')
        row['components'].append({'name': component.get_name(), 'class': component.get_class().get_name(),
                                  'values': {key: value(component, key) for key in fields}})
    if isinstance(actor, u.PostProcessVolume):
        settings = actor.get_editor_property('settings')
        row['post_process'] = {key: value(settings, key) for key in (
            'override_auto_exposure_min_brightness', 'override_auto_exposure_max_brightness',
            'auto_exposure_min_brightness', 'auto_exposure_max_brightness',
            'override_auto_exposure_bias', 'auto_exposure_bias')}
    report['actors'].append(row)

bp = u.load_asset('/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky')
cls = u.load_object(None, '/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C')
cdo = u.get_default_object(cls)
old = json.loads((ROOT/'SourceAssets/UDSBridge20261017/probe13.json').read_text(encoding='utf-8'))
for name in old['sky_hit_props']:
    if any(word in name.lower() for word in ('moon', 'sun', 'exposure', 'time', 'night', 'sky light', 'tick', 'refresh', 'update')):
        report['sky_defaults'][name] = value(cdo, name)
graphs = u.BlueprintEditorLibrary.list_graphs(bp)
report['graphs'] = [g.get_name() for g in graphs]
for i, graph in enumerate(graphs):
    name = graph.get_name()
    if any(word in name.lower() for word in ('tick', 'priority updates', 'time of day', 'sun and moon', 'time cycle', 'eventgraph')):
        export(graph, 'graph-%03d.t3d' % i)
        report.setdefault('graph_exports', {})['graph-%03d.t3d' % i] = name
(OUT/'before.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('HILLS_NIGHT_INSPECTION_SAVED ' + str(OUT/'before.json'))
