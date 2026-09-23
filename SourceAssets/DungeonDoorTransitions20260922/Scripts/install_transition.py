"""Production import and scoped map patch. Does not regenerate rooms or start play."""
import unreal as u,json,runpy,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Randomized'
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);ed=u.get_editor_subsystem(u.LevelEditorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve running game')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map before installation')
def stage(path):
    state=runpy.run_path(str(path),run_name='__main__');del state;gc.collect()
stage(ROOT/'Scripts/import_transition.py')
if ue.get_editor_world().get_path_name().split('.')[0]!=TARGET and not ed.load_level(TARGET):raise RuntimeError('Cannot load random dungeon')
stage(ROOT/'Scripts/apply_start_connection.py')
stage(ROOT.parent/'DungeonRoutes20260922/Scripts/build_catalog.py')
# Keep the already generated layout and its current material overrides. Only add the interface metadata.
recipe=json.loads((ROOT/'Config/transition.json').read_text())
catalog=json.loads((ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').read_text(encoding='utf-8'))
metadata={m['id']:m for m in catalog['modules']}
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label()!='DGN_RouteGenerator':continue
    current=json.loads(actor.get_editor_property('module_catalog_json'));current['start_connection']=recipe
    for module in current['modules']:
        if module['id'] in ('Transit','Threshold'):module['ports']=metadata[module['id']]['ports']
    actor.modify();actor.set_editor_property('module_catalog_json',json.dumps(current))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save connector actor packages')
if not ed.save_current_level():raise RuntimeError('Cannot save random dungeon')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,mesh=recipe['mesh'],entry_clear_m=recipe['entry_clear_m'],exit_clear_m=recipe['exit_clear_m'],saved_packages=len(owned),tests_run=False),indent=2))
print('START_TRANSITION_MAP_SAVED',TARGET)
