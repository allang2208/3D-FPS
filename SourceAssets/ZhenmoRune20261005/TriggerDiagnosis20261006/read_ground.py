"""Read current ground collision used by the Bagua mesh, without any mutation."""
from pathlib import Path
import json
import unreal as u
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
a=u.GameplayStatics.get_player_character(w,0) if w else None
if not w:
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
out={'world':w.get_path_name() if w else None,'samples':[]}
if w:
    p=a.get_actor_location() if a else u.Vector(7193.703013,-1156.035333,386.149999)
    if a:
        p.z-=a.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    out['feet']=str(p)
    for complex_trace in (True,False):
        for x,y in ((0,0),(-430,0),(430,0),(0,-430),(0,430)):
            hits=u.SystemLibrary.line_trace_multi_for_objects(w,u.Vector(p.x+x,p.y+y,p.z+100),
                u.Vector(p.x+x,p.y+y,p.z-350),
                [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],
                complex_trace,[a] if a else [],u.DrawDebugTrace.NONE,True)
            out['samples'].append({'complex':complex_trace,'offset':[x,y],
                                   'hits':[str(h.to_dict()) for h in hits or []]})
(Path(__file__).resolve().parent/'ground_state.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('ZHENMO_GROUND '+json.dumps(out))
