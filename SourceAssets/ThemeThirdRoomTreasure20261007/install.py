"""Save only the two missing subject treasures and their production descriptors."""
import json
import runpy
import shutil
import traceback
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
T = runpy.run_path(str(ROOT / 'treasure.py'))
PRODUCTION = '/Game/GameMaps/L_Dungeon_Randomized'
RECEIPT = ROOT / 'Receipts/install.json'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE_ACTIVE: preserve running editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('DIRTY_MAP: preserve unsaved maps')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    previous = editor.get_editor_world()
    previous = previous.get_path_name().split('.')[0] if previous else None
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    hospital = json.loads((PROJECT / 'SourceAssets/DungeonHospitalLine20261003/Config/line.json').read_text('utf8'))
    power = json.loads((PROJECT / 'SourceAssets/DungeonPowerTheme20261004RefineV2/Config/module-drafts.json').read_text('utf8'))
    targets = [
        (hospital['map'], next(p for p in hospital['placements'] if p['id'] == 'AbandonedAnatomyTheatre'), 'HospitalLine.Subject'),
        ('/Game/GameMaps/Design/L_PowerTheme20261004_Subject',
         next(p for p in power['subject_placements'] if p['id'] == 'AccumulatorControl'), 'PowerTheme.Subject'),
    ]
    cache = {}

    def load(path):
        if path not in cache:
            cache[path] = u.load_asset(path)
            if not cache[path]:
                raise RuntimeError('Missing existing treasure asset: ' + path)
        return cache[path]

    for module_id in T['PLACEMENTS']:
        for path in T['asset_paths'](T['spec'](module_id)):
            load(path)
    load(T['BLUEPRINT'])
    backup = ROOT / 'Backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True, exist_ok=True)

    def save(world, path):
        disk = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.umap')
        if disk.exists():
            shutil.copy2(disk, backup / disk.name)
        if not u.EditorLoadingAndSavingUtils.save_map(world, path):
            raise RuntimeError('Map save failed: ' + path)

    report = dict(stage='saving', subject_maps=[], production_modules_added=[],
        existing_themes_untouched=['freight', 'treatment', 'staff_living', 'ecology'],
        tests_run=False, game_run=False, rendered=False, editor_opened=False)
    write(RECEIPT, report)
    try:
        for path, pose, tag in targets:
            world = u.EditorLoadingAndSavingUtils.load_map(path)
            if not world:
                raise RuntimeError('Subject map could not be loaded: ' + path)
            # Preserve a new third-room chest if another author added one since capture.
            def in_third_room(actor):
                p = actor.get_actor_location()
                x, y = p.x - pose['position'][0], p.y - pose['position'][1]
                return (abs(x) <= 1700 and abs(y) <= 1450 if pose['id'] == 'AbandonedAnatomyTheatre'
                        else x*x + y*y <= 2250*2250)
            existing = [a for a in actors.get_all_level_actors()
                        if a.actor_has_tag(u.Name('DungeonTreasureChest')) and in_third_room(a)]
            if existing:
                report['subject_maps'].append(dict(map=path, status='existing_skipped', labels=[a.get_actor_label() for a in existing]))
                write(RECEIPT, report)
                continue
            chest = T['spec'](pose['id'])
            actor = T['spawn_subject'](actors, load, chest, pose, path, tag)
            save(world, path)
            position = actor.get_actor_location()
            report['subject_maps'].append(dict(map=path, module=pose['id'], status='saved',
                identity=chest['identity'], local_position=chest['position'],
                world_position=[position.x, position.y, position.z], yaw=chest['yaw']))
            write(RECEIPT, report)
        world = u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
        generators = [a for a in actors.get_all_level_actors() if isinstance(a, u.AuthoredDungeonGenerator)]
        if len(generators) != 1:
            raise RuntimeError('Expected one production generator; preserve catalog')
        generator = generators[0]
        before = json.loads(generator.get_editor_property('module_catalog_json'))
        after = T['extend'](before)
        for old, new in zip(before['modules'], after['modules']):
            if old != new:
                report['production_modules_added'].append(new['id'])
        if after != before:
            write(backup / 'production-catalog.json', before)
            assets = {a.get_path_name(): a for a in generator.get_editor_property('module_assets') if a}
            for module_id in report['production_modules_added']:
                for path in T['asset_paths'](T['spec'](module_id)):
                    asset = load(path)
                    assets[asset.get_path_name()] = asset
            generator.modify()
            generator.set_editor_property('module_catalog_json', json.dumps(after, ensure_ascii=False))
            generator.set_editor_property('module_assets', list(assets.values()))
            save(world, PRODUCTION)
        report['production_map'] = PRODUCTION
        report['production_status'] = 'saved' if after != before else 'existing_skipped'
        report['power_route_registered'] = any(r['sequence'][-1] == 'AccumulatorControl' for r in after.get('themed_routes', {}).get('routes', []))
        report['stage'] = 'maps_saved'
        write(RECEIPT, report)
        if not commandlet and previous:
            u.EditorLoadingAndSavingUtils.load_map(previous)
        print('THIRD_ROOM_TREASURES_SAVED ' + json.dumps(report, ensure_ascii=False))
    except Exception:
        report.update(stage='save_failed', error=traceback.format_exc())
        write(RECEIPT, report)
        raise


if __name__ == '__main__':
    main()
