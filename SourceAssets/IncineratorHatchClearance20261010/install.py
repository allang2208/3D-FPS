"""Save the cabinet relocation in production and the retained incinerator subject."""
from pathlib import Path
from datetime import datetime
import json
import math
import runpy
import shutil
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
FLOW = PROJECT / 'SourceAssets/DungeonFacilityFlow20261007'
CONTAINERS = PROJECT / 'SourceAssets/IncineratorContainers20261003'
LINE = PROJECT / 'SourceAssets/DungeonIncineratorLine20261003'
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
SUBJECT = '/Game/GameMaps/Design/L_Incinerator_Theme_Subject'
R = runpy.run_path(str(ROOT / 'recipe.py'))
save = runpy.run_path(str(PROJECT / 'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
read = lambda p: json.loads(p.read_text('utf-8-sig'))


def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve active gameplay and unsaved maps')
    previous = editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
    report = dict(stage='preparing', revision=R['REVISION'], game_run=False,
                  tested=False, rendered=False, maps=[], mirrors=[])
    receipts = ROOT / 'Receipts'
    receipts.mkdir(exist_ok=True)
    backup = ROOT / 'Backups' / datetime.now().strftime('%Y%m%d-%H%M%S')

    def record():
        (receipts / 'install.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')

    def preserve(path):
        if path.exists():
            dest = backup / path.relative_to(PROJECT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)

    def write(path, value, compact=False):
        preserve(path)
        path.write_text(json.dumps(value, ensure_ascii=False,
                                  **({'separators': (',', ':')} if compact else {'indent': 2})), encoding='utf8')
        report['mirrors'].append(str(path.relative_to(PROJECT)))

    try:
        for target in (TARGET, SUBJECT):
            relative = target.removeprefix('/Game/')
            preserve(PROJECT / 'Content' / (relative + '.umap'))
            for category in ('__ExternalActors__', '__ExternalObjects__'):
                folder = PROJECT / 'Content' / category / relative
                if folder.exists():
                    for path in folder.rglob('*'):
                        if path.is_file():
                            preserve(path)
        report['backup'] = str(backup)
        record()
        world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
        if len(generators) != 1:
            raise RuntimeError('Expected the saved production generator')
        generator = generators[0]
        raw = generator.get_editor_property('module_catalog_json')
        (backup / 'catalog-before.json').write_text(raw, encoding='utf8')
        catalog = json.loads(raw)
        contract = runpy.run_path(str(FLOW / 'restore_entry_recipe.py'))['contract_hash']
        bank = catalog['facility_flow']['layout_bank']
        if bank['contract_sha1'] != contract(catalog):
            raise RuntimeError('Preserve an inconsistent production layout bank')
        module = next(m for m in catalog['modules'] if m['id'] == R['MODULE'])
        if not R['apply_module'](module):
            raise RuntimeError('Target cabinet bay is missing; preserve the current catalog')
        bank['contract_sha1'] = contract(catalog)
        generator.modify()
        generator.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
        save(world, TARGET)
        report['maps'].append(dict(path=TARGET, saved=True, cabinet_bays_changed=1))
        write(FLOW / 'Config/catalog.json', catalog)
        write(FLOW / 'Config/layout-bank-v1.json', bank, compact=True)
        report['stage'] = 'production_saved'
        record()

        # Move only the two existing searchable actors; retain their identities,
        # inventory settings, hinge transforms and all unrelated subject dressing.
        world = u.EditorLoadingAndSavingUtils.load_map(SUBJECT)
        pose = next(p for p in read(LINE / 'Config/line.json')['placements'] if p['id'] == R['MODULE'])
        specs = {s['container_id']: s for g in module['warehouse_containers']['groups']
                 for slot in g['slots'] if slot['id'] == R['SLOT']
                 for variant in slot['variants'] for s in variant['containers']}
        moved = []
        angle = math.radians(pose['yaw'])
        c, s = math.cos(angle), math.sin(angle)
        for actor in u.GameplayStatics.get_all_actors_of_class(world, u.ColdSteelSceneContainer):
            identity = str(actor.get_editor_property('container_id'))
            local_id = identity.removeprefix('IncineratorLine.')
            if identity == local_id or local_id not in specs:
                continue
            spec = specs[local_id]
            x, y, z = spec['position']
            o = pose['position']
            actor.modify()
            actor.set_actor_location_and_rotation(
                u.Vector(o[0]+c*x-s*y, o[1]+s*x+c*y, o[2]+z),
                u.Rotator(pitch=0, yaw=pose['yaw']+spec['yaw'], roll=0), False, True)
            moved.append(identity)
        save(world, SUBJECT)
        report['maps'].append(dict(path=SUBJECT, saved=True, moved_containers=moved))
        record()

        layout = read(CONTAINERS / 'Config/layout.json')
        R['apply_layout'](layout)
        write(CONTAINERS / 'Config/layout.json', layout)
        # Keep the live authoring inputs consistent without replacing full catalogs
        # from old source snapshots. Every update touches only this named bay.
        for path in (LINE / 'Config/source-modules.json',
                     PROJECT / 'SourceAssets/DungeonIncineratorHall20260929/Pool20260930/Config/module.json',
                     CONTAINERS / 'Config/placement-source.json',
                     CONTAINERS / 'Config/catalog.json'):
            if not path.exists():
                continue
            data = read(path)
            modules = data.get('modules', [data])
            changed = [R['apply_module'](m) for m in modules]
            if any(changed):
                if data.get('facility_flow', {}).get('layout_bank'):
                    data['facility_flow']['layout_bank']['contract_sha1'] = contract(data)
                write(path, data)
        report.update(stage='maps_saved', bay=R['bay'](), bank_contract_sha1=bank['contract_sha1'])
        record()
        print('INCINERATOR_HATCH_CLEARANCE_SAVED', json.dumps(report['maps'], ensure_ascii=False))
    except Exception:
        report['error'] = traceback.format_exc()
        record()
        raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)


if __name__ == '__main__':
    main()
