"""Remove the identified floating PWL tutorial advert from the main map only."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME')
out=root/'Saved/HillsSkyMarkers20260915'
out.mkdir(parents=True,exist_ok=True)
source=root/'Content/GameMaps/DayNight_Lighting.umap'
backup=out/('BeforeDemoTextRemoval-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
shutil.copy2(source,backup/source.name)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
if not levels.load_level('/Game/GameMaps/DayNight_Lighting'):
    raise RuntimeError('Unable to load DayNight_Lighting')
removed=[]
for a in actors.get_all_level_actors():
    if not isinstance(a,u.TextRenderActor):continue
    t=a.get_component_by_class(u.TextRenderComponent)
    text=str(t.get_editor_property('text')) if t else ''
    if text.startswith('Hello Copy me to a text editor,') and 'proceduralworldLab.com' in text:
        removed.append({'actor':a.get_path_name(),'label':a.get_actor_label(),'text':text})
        if not actors.destroy_actor(a):raise RuntimeError('Unable to remove identified demo advert')
if removed and not levels.save_current_level():raise RuntimeError('Unable to save main level')
(out/'removed-demo-text.json').write_text(json.dumps({'removed':removed,'backup':str(backup)},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('DAYNIGHT_DEMO_TEXT_REMOVED '+str(len(removed)))
