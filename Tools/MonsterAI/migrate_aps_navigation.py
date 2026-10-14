"""Migrate supported agents configured for APS nav data and rebuild saved tiles."""
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
OUTPUT = PROJECT / 'Saved/APSNavigationMigration'
MAPS = ['/Game/GameMaps/DayNight_Lighting', '/Game/GameMaps/L_Dungeon_Randomized']

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Run with PythonScript commandlet while the project editor is closed.')

OUTPUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUTPUT / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
BACKUP.mkdir()
report = dict(backups=[], migration=[], runtime_tested=False, visual_tested=False, complete=False)


def record():
    (OUTPUT / 'migration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def backup(package):
    source = PROJECT / ('Content/' + package.removeprefix('/Game/') + '.umap')
    destination = BACKUP / (source.stem + '.umap')
    shutil.copy2(source, destination)
    report['backups'].append(dict(source=str(source), backup=str(destination)))
    record()


try:
    for package in MAPS:
        backup(package)
        migration = json.loads(u.MonsterAPSMigration.migrate_navigation_to_aps(package))
        report['migration'].append(migration)
        record()
        if not migration.get('saved') or not (migration.get('navigation_built') or migration.get('runtime_template_saved')):
            raise RuntimeError('APS navigation migration failed: ' + json.dumps(migration, ensure_ascii=False))
    report['complete'] = True
    record()
    print('APS_NAVIGATION_MIGRATED ' + str(OUTPUT / 'migration.json'), flush=True)
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
