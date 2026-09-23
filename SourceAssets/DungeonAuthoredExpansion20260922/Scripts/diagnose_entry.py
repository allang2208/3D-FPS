"""Read only the loaded dungeon, relevant entrances, and expansion geometry."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[1]
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
def vec(v):return [round(v.x,2),round(v.y,2),round(v.z,2)]
def describe(w):
    if not w:return None
    actors=list(u.GameplayStatics.get_all_actors_of_class(w,u.Actor))
    result={'world':w.get_path_name(),'actors':len(actors),'segments':{k:sum(a.get_actor_label().startswith('DGN_'+k+'_') for a in actors) for k in ['A','B']},'relevant':[]}
    pawn=u.GameplayStatics.get_player_pawn(w,0)
    result['pawn']=vec(pawn.get_actor_location()) if pawn else None
    for a in actors:
        label=a.get_actor_label()
        if not (any(s in label for s in ['EntryEnd','EndLanding','ServiceDoor','DGN_Link','SceneTestPortal']) or isinstance(a,u.PlayerStart)):continue
        row={'label':label,'class':a.get_class().get_name(),'position':vec(a.get_actor_location()),'rotation':str(a.get_actor_rotation()),'scale':vec(a.get_actor_scale3d())}
        c=a.get_component_by_class(u.StaticMeshComponent)
        if c and c.static_mesh:
            row['mesh']=c.static_mesh.get_path_name();row['bounds']=[vec(v) for v in a.get_actor_bounds(False)]
        text=a.get_component_by_class(u.TextRenderComponent)
        if text:row['text']=str(text.get_editor_property('text'))
        if a.get_class().get_name()=='SceneTestPortal':
            for prop in ['destination','destination_label']:
                try:row[prop]=str(a.get_editor_property(prop))
                except Exception:pass
        result['relevant'].append(row)
    return result
report={'editor':describe(ue.get_editor_world()),'game':describe(ue.get_game_world()),'dirty':[p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]}
(root/'Receipts/entry-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
