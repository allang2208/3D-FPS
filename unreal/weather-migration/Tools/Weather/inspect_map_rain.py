import unreal,json
from pathlib import Path
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report={}
for name in ['L_Normandy_FPS_Test','L_MilitaryTrench_FPS_Test','DayNight_Lighting']:
    assert editor.load_level('/Game/GameMaps/'+name)
    rows=[]
    for a in actors.get_all_level_actors():
        for c in a.get_components_by_class(unreal.NiagaraComponent):
            s=c.get_asset()
            rows.append(dict(actor=a.get_actor_label(),component=c.get_name(),system=s.get_path_name() if s else '',location=str(c.get_world_location())))
    report[name]=rows
(Path(unreal.Paths.project_saved_dir())/'RainUpgrade/map-niagara.json').write_text(json.dumps(report,indent=2))
unreal.log('RAIN_MAP_INSPECT_PASS')
