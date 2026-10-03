"""Locate the reported placed bench across loaded PIE worlds without changing it."""
import json,datetime,collections
from pathlib import Path
import unreal as u
def path(obj):return obj.get_path_name() if obj else None
result=[]
worlds=list(u.EditorLevelLibrary.get_pie_worlds(False))
for world in worlds:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
    entry={'world':path(world),'player':path(pawn),'player_location':str(pawn.get_actor_location()) if pawn else None,
        'actor_count':len(actors),'prefab_classes':dict(collections.Counter(a.get_class().get_name() for a in actors if 'Voxel' in a.get_class().get_name())),
        'matches':[],'nearby':[]}
    for actor in actors:
        distance=actor.get_distance_to(pawn) if pawn else None
        for component in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=component.static_mesh
            if not mesh:continue
            record={'actor':path(actor),'class':actor.get_class().get_name(),'component':path(component),'mesh':path(mesh),'distance_cm':distance}
            if any(s in path(mesh).lower() for s in ['workbench','tasklamp','lampflex']):entry['matches'].append(record)
            elif distance is not None and distance<600:entry['nearby'].append(record)
    entry['matches'].sort(key=lambda x:x['distance_cm'] or 0)
    entry['nearby'].sort(key=lambda x:x['distance_cm'] or 0)
    result.append(entry)
root=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchVisibleFix20260928')
filename='locate-'+datetime.datetime.now().strftime('%H%M%S')+'.json'
(root/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file':filename,'worlds':[{k:v for k,v in e.items() if k!='nearby'} for e in result]},ensure_ascii=False))
