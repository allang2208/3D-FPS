"""Save the medical theatre corner chest into the current production catalog."""
import json
import runpy
import shutil
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
MAP = '/Game/GameMaps/L_Dungeon_Randomized'
MODULE = 'AbandonedAnatomyTheatre'
T = runpy.run_path(str(PROJECT / 'SourceAssets/ThemeThirdRoomTreasure20261007/treasure.py'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project for the medical chest installation')
    background = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not background:
        raise RuntimeError('This scoped map save requires the background commandlet')
    report = dict(stage='saving', map=MAP, module=MODULE, tests_run=False, game_run=False)
    receipt = ROOT / 'Receipts/install.json'
    write(receipt, report)
    try:
        map_file = PROJECT / 'Content/GameMaps/L_Dungeon_Randomized.umap'
        backup = ROOT / 'Backups/L_Dungeon_Randomized.umap'
        if not backup.exists():
            shutil.copy2(map_file, backup)
        world = u.EditorLoadingAndSavingUtils.load_map(MAP)
        if not world:
            raise RuntimeError('Could not load the production map')
        generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
        if len(generators) != 1:
            raise RuntimeError('Expected one production generator; no map changes saved')
        generator = generators[0]
        before = generator.get_editor_property('module_catalog_json')
        catalog = json.loads(before)
        matches = [m for m in catalog['modules'] if m['id'] == MODULE]
        if len(matches) != 1:
            raise RuntimeError('Expected one medical theatre module')
        module = T['extend_module'](matches[0])
        chest = next(p for p in module['props']
                     if p.get('identity') == T['PLACEMENTS'][MODULE]['identity'])
        assets = {a.get_path_name(): a for a in generator.get_editor_property('module_assets') if a}
        for path in T['asset_paths'](chest):
            asset = u.load_asset(path)
            if not asset:
                raise RuntimeError('Missing chest dependency: ' + path)
            assets[asset.get_path_name()] = asset
        (ROOT / 'Backups/production-catalog.json').write_text(before, encoding='utf8')
        catalog['modules'] = [module if m['id'] == MODULE else m for m in catalog['modules']]
        generator.modify()
        generator.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
        generator.set_editor_property('module_assets', list(assets.values()))
        if not u.EditorLoadingAndSavingUtils.save_map(world, MAP):
            raise RuntimeError('Production map save failed')
        # Patch only the matching module in the author descriptors, not a stale
        # whole-catalog snapshot over concurrent source work.
        for relative in (
            'SourceAssets/DungeonAnatomyTheatre20261001/Pool20261001/Config/module.json',
            'SourceAssets/DungeonRoutes20260922/Config/catalog.json',
        ):
            path = PROJECT / relative
            data = json.loads(path.read_text(encoding='utf8'))
            if 'modules' in data:
                data['modules'] = [T['extend_module'](m) if m['id'] == MODULE else m for m in data['modules']]
            else:
                data = T['extend_module'](data)
            write(path, data)
        report.update(stage='map_saved', position=chest['position'], yaw=chest['yaw'],
                      identity=chest['identity'], interaction_enabled=chest['interaction_enabled'],
                      chest_count=sum(T['is_treasure'](p) for p in module['props']))
        write(receipt, report)
        print('MEDICAL_CORNER_CHEST_SAVED ' + json.dumps(report, ensure_ascii=False), flush=True)
    except Exception:
        report.update(stage='save_failed', error=traceback.format_exc())
        write(receipt, report)
        raise


if __name__ == '__main__':
    main()
