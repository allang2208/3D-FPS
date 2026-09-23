"""Read only: never switch map, generate, play, modify, load room meshes or save packages."""
import json
from pathlib import Path
import unreal as u
out=Path(__file__).resolve().parents[1]/'Results'
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ue.get_editor_world()
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
result={'editor_world':world.get_path_name() if world else None,
        'play_world':str(ue.get_game_world()),'generators':[], 'navigation':[]}
for a in actors:
    cls=a.get_class().get_name()
    if 'NavMeshBoundsVolume' in cls:
        origin,extent=a.get_actor_bounds(False)
        result['navigation'].append({'class':cls,'origin':str(origin),'extent':str(extent)})
    if cls!='AuthoredDungeonGenerator':continue
    item={'label':a.get_actor_label()}
    for key in ('module_catalog_json','layout_manifest_json','layout_description','generated_seed','randomize_on_entry'):
        try:item[key]=a.get_editor_property(key)
        except Exception as e:item[key]='UNAVAILABLE '+str(e)
    try:item['hard_assets']=[x.get_path_name() for x in a.get_editor_property('module_assets') if x]
    except Exception as e:item['asset_error']=str(e)
    result['generators'].append(item)
(out/'editor-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'world':result['editor_world'],'play':result['play_world'],
    'generators':[dict(label=g['label'],description=g.get('layout_description')) for g in result['generators']],
    'nav_volumes':len(result['navigation'])},ensure_ascii=False))
