from pathlib import Path
import json
import unreal as u
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
def path(o):return o.get_path_name() if o else None
report=dict(editor=path(ed.get_editor_world()),game=path(ed.get_game_world()),
    generators=[path(o) for o in u.ObjectIterator(u.AuthoredDungeonGenerator)],
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
for p in ('/Game/GameMaps/L_Dungeon_Randomized','/Game/GameMaps/Design/L_ReceptionHall_Subject',
          '/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject'):
    world=u.find_object(None,p+'.'+p.rsplit('/',1)[-1])
    report.setdefault('loaded_targets',[]).append(dict(path=p,loaded=bool(world)))
(Path(__file__).resolve().parent/'Receipts/loaded-targets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
