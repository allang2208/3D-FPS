"""Apply authored hall lighting in a serialized background save; no game run."""
import json
import runpy
import shutil
import traceback
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
P=runpy.run_path(str(ROOT/'profile.py'))
PROJECT=P['PROJECT']
MAPS=['/Game/GameMaps/Design/'+n for n in ('L_ReceptionHall_Subject','L_FacilityTransit_Subject','L_FacilityTransit_Alternate_Subject')]


def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved work')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);previous=editor.get_editor_world()
    previous=previous.get_path_name().split('.')[0] if previous else None
    report=dict(stage='authoring',maps=[],tests_run=False,rendered=False,game_run=False,editor_opened=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    try:
        materials=runpy.run_path(str(ROOT/'author_materials.py'))
        report['saved_assets']=materials['main']();report['stage']='assets_saved';record()
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
        for path in MAPS:
            disk=PROJECT/'Content'/(path.removeprefix('/Game/')+'.umap')
            shutil.copy2(disk,backup/disk.name)
            world=u.EditorLoadingAndSavingUtils.load_map(path)
            if not world:raise RuntimeError('Unable to load hall '+path)
            changes=P['apply_world']()
            u.EditorAssetLibrary.set_metadata_tag(world,'HallLighting.Revision',P['REVISION'])
            if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Unable to save hall '+path)
            report['maps'].append(dict(path=path,saved=True,changes=changes));record()
        report['stage']='maps_saved';record()
        if not commandlet and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
        print('ABANDONED_HALL_LIGHTING_SAVED '+json.dumps(report,ensure_ascii=False))
    except Exception:
        report.update(stage='save_failed',error=traceback.format_exc());record();raise


if __name__=='__main__':main()
