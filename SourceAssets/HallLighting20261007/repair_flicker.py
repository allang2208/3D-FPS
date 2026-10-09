"""Replace the saved faulty-lamp shaders, preserving all map geometry and live edits."""
import json, runpy, shutil, traceback
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
P=runpy.run_path(str(ROOT/'profile.py'))
if Path(u.Paths.project_dir()).resolve()!=P['PROJECT'].resolve():raise RuntimeError('Wrong project')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE_ACTIVE: preserve the running editor')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if any(p.startswith(P['BASE']+'/') for p in dirty):raise RuntimeError('Preserve unsaved hall lighting materials')

report=dict(stage='authoring',revision=P['REVISION'],game_run=False,maps_modified=False,
    checks=['saved map bindings','lamp vertex mask coverage','render switches','target SM6 shader compilation'],
    visual_playtest=False,cycle_seconds=[6.4,8.6],blackout_seconds=[.98,1.43],assets=[],shader_statistics=[])
def record():
    (ROOT/'Receipts/flicker-repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
record()
try:
    source=P['PROJECT']/'Content/Dungeons/HallLighting20261007/Materials'
    backup=ROOT/'Backups'/('flicker-v1-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=True)
    for asset in source.glob('*.uasset'):shutil.copy2(asset,backup/asset.name)
    report['backup']=str(backup)
    report['assets']=runpy.run_path(str(ROOT/'author_materials.py'))['main']()
    report['stage']='materials_saved';record()
    # Uses the current RHI. This compiles the saved materials, without starting
    # PIE, opening the editor, or rendering a playtest of the hall.
    for name in ('M_FaultFunction','M_ReceptionDiffusers','M_TransitDiffusers'):
        m=u.load_asset(P['material'](name))
        report['shader_statistics'].append(dict(path=m.get_path_name(),
            statistics=str(u.MaterialEditingLibrary.get_statistics(m))))
    report['stage']='saved_and_compiled';record()
    print('HALL_FLICKER_REPAIR_SAVED',json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
