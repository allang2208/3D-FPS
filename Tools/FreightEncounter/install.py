"""Save the moved freight chest and existing upper-platform spawn mask."""
import json,runpy,shutil,traceback
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/FreightEncounter20261014'
for name in ['Backups','Receipts']:(ROOT/name).mkdir(parents=True,exist_ok=True)
PATCH=runpy.run_path(str(PROJECT/'Tools/FreightEncounter/catalog_patch.py'))
MAP='/Game/GameMaps/L_Dungeon_Randomized'
report=dict(stage='saving',map=MAP,game_run=False,tests_run=False)

def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project; no map changes performed')
    background='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    original=None
    if not background:
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level.is_in_play_in_editor():raise RuntimeError('PIE active; no production map changes performed')
        original=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
        dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        if original!=MAP and dirty:raise RuntimeError('Unsaved map changes exist; preserve them before switching maps')
        if any(str(p.get_name())==MAP for p in dirty):raise RuntimeError('Production map has unsaved edits; do not overwrite them')
    backup=ROOT/'Backups/L_Dungeon_Randomized.umap'
    if not backup.exists():shutil.copy2(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',backup)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Could not load production map')
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Expected one production generator')
    generator=generators[0];before=generator.get_editor_property('module_catalog_json');catalog=json.loads(before)
    module=next(m for m in catalog['modules'] if m['id']==PATCH['STATION'])
    chest=next(p for p in module.get('props',[]) if p.get('identity')==PATCH['CHEST_ID'])
    report['previous_chest_position']=chest['position']
    previous=ROOT/'Backups/production-catalog.json'
    if not previous.exists():previous.write_text(before,encoding='utf8')
    updated=PATCH['patch_document'](catalog)
    generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(updated,ensure_ascii=False))
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Production map save failed')
    report['stage']='map_saved';record()
    report['sources_saved']=PATCH['update_sources'](PROJECT,ROOT)
    report.update(stage='saved',chest_identity=PATCH['CHEST_ID'],chest_position=PATCH['CHEST_POSITION'],
        upper_walk_mask=PATCH['UPPER_WALK'],interaction_and_loot='preserved',rendered=False)
    record()
    if original and original!=MAP:u.EditorLoadingAndSavingUtils.load_map(original)
    print('FREIGHT_MAP_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)

try:
    record();main()
except Exception:
    report.update(stage='save_failed',error=traceback.format_exc());record();raise
