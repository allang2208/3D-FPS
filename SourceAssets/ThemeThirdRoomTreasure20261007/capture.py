"""Read the saved route catalog and existing subject treasures for requested placement work."""
import unreal as u
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
for f in ('Config','Receipts'):(ROOT/f).mkdir(parents=True,exist_ok=True)
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running editor')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved work')
previous=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
previous=previous.get_path_name().split('.')[0] if previous else None
report=dict(stage='read_saved_placements',maps=[],tests_run=False)
maps=['/Game/GameMaps/L_Dungeon_Randomized']+['/Game/GameMaps/Design/'+n for n in ('L_FreightTransit_Theme_Subject','L_Hospital_Theme_Subject','L_Incinerator_Theme_Subject','L_Ecology_Theme_Subject','L_PowerTheme20261004_Subject','L_StaffLiving_Theme_Subject')]
for path in maps:
    entry=dict(path=path,exists=E.does_asset_exist(path));report['maps'].append(entry)
    if not entry['exists']:continue
    world=u.EditorLoadingAndSavingUtils.load_map(path)
    chests=[]
    for a in AA.get_all_level_actors():
        if isinstance(a,u.AuthoredDungeonGenerator):
            data=json.loads(a.get_editor_property('module_catalog_json'));(ROOT/'Config/production-catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
            entry['routes']=data.get('themed_routes',{}).get('routes',[])
            entry['third_rooms']=[dict(route=r['id'],module=r['sequence'][-1],props=next(m for m in data['modules'] if m['id']==r['sequence'][-1]).get('props',[])) for r in entry['routes']]
        if a.actor_has_tag(u.Name('DungeonTreasureChest')):
            p=a.get_actor_location();chests.append(dict(label=a.get_actor_label(),position=[p.x,p.y,p.z],yaw=a.get_actor_rotation().yaw,tags=[str(t) for t in a.tags]))
    entry['chests']=chests
(ROOT/'Config/saved-placements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
print('THIRD_ROOM_PLACEMENTS_READ',json.dumps([dict(map=e['path'],exists=e['exists'],chests=len(e.get('chests',[]))) for e in report['maps']]))
