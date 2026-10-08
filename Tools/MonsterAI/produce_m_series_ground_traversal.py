"""Save existing M10/M14/M25 movement templates and their production navigation."""
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
OUTPUT = PROJECT / 'Saved/MSeriesGroundTraversal20261006'
PROFILES = [
    ('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler', 225.0, 450.0),
    ('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14', 125.0, 300.0),
    ('/Game/Monsters/VortexCofferM25/BP_VortexCofferM25', 225.0, 450.0),
]
MAPS = ['/Game/GameMaps/DayNight_Lighting', '/Game/GameMaps/L_Dungeon_Randomized']

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Run with PythonScript commandlet while the project editor is closed.')

OUTPUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUTPUT / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
BACKUP.mkdir()
report = dict(saved_assets=[], backups=[], runtime_tested=False, visual_tested=False, complete=False)
navigation_only = '-mseriesnavigationonly' in u.SystemLibrary.get_command_line().lower()
if navigation_only:
    report = json.loads((OUTPUT / 'production.json').read_text(encoding='utf-8'))
    report.pop('error', None)


def record():
    (OUTPUT / 'production.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def backup(package, extension):
    source = PROJECT / ('Content/' + package.removeprefix('/Game/') + extension)
    destination = BACKUP / (source.stem + extension)
    shutil.copy2(source, destination)
    report['backups'].append(dict(source=str(source), backup=str(destination)))
    record()


try:
    for package, radius, height in ([] if navigation_only else PROFILES):
        backup(package, '.uasset')
        blueprint = u.load_asset(package)
        if not blueprint:
            raise RuntimeError('Missing existing monster blueprint: ' + package)
        u.BlueprintEditorLibrary.compile_blueprint(blueprint)
        defaults = u.get_default_object(blueprint.generated_class())
        movement = defaults.get_editor_property('character_movement')
        movement.set_editor_property('max_step_height', 40.0)
        movement.set_editor_property('use_flat_base_for_floor_checks', False)
        agent = movement.get_editor_property('nav_agent_props')
        agent.set_editor_property('agent_radius', radius)
        agent.set_editor_property('agent_height', height)
        agent.set_editor_property('agent_step_height', 40.0)
        movement.set_editor_property('nav_agent_props', agent)
        policy = movement.get_editor_property('nav_movement_properties')
        policy.set_editor_property('update_nav_agent_with_owners_collision', False)
        movement.set_editor_property('nav_movement_properties', policy)
        if not u.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
            raise RuntimeError('Blueprint save failed: ' + package)
        report['saved_assets'].append(dict(package=package, radius_cm=radius, height_cm=height, step_cm=40.0))
        record()
    report['navigation'] = []
    for package in MAPS:
        backup(package, '.umap')
        navigation = json.loads(u.M10Mawcrawler.build_map_navigation(package))
        report['navigation'].append(navigation)
        record()
        if not navigation.get('saved') or not (navigation.get('navigation_built') or navigation.get('runtime_template_saved')):
            raise RuntimeError('Navigation production failed: ' + json.dumps(navigation, ensure_ascii=False))
    report['complete'] = True
    record()
    print('M_SERIES_GROUND_TRAVERSAL_SAVED ' + str(OUTPUT / 'production.json'), flush=True)
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
