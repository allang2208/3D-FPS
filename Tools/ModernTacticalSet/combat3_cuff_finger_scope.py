"""Record whether the wrist correction touched finger-dominant vertices."""
import json,math
from pathlib import Path
C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
rows=read(C/'captured.json')['rows'];result={}
for rig in ['Body','Super90']:
    original=read(next(row['file'] for row in rows if row['key']=='Glove_'+rig));edited=read(C/'Authored'/f'gloves_{rig}.json');count=0;maximum=0.;materials={};vertex_materials={};forearm_distances=[];bones={b['name']:b for b in edited['bones']}
    for face,mi in zip(original['triangles'],original['triangle_materials']):
        for vi in face:vertex_materials.setdefault(vi,set()).add(original['material_slots'][mi])
    for vi,(a,b,ws) in enumerate(zip(original['positions'],edited['positions'],original['weights'])):
        influence=sum(v for name,v in ws.items() if name.startswith(('thumb','index','middle','ring','pinky')))
        if influence>.5:
            distance=math.dist(a,b)
            if distance>1e-5:
                count+=1;maximum=max(maximum,distance)
                side=max(['l','r'],key=lambda s:sum(value for name,value in ws.items() if name.endswith('_'+s)));w=bones['hand_'+side]['position'];e=bones['lowerarm_'+side]['position'];axis=[x-y for x,y in zip(w,e)];length=math.sqrt(sum(x*x for x in axis));forearm_distances.append(-sum((x-y)*z/length for x,y,z in zip(a,w,axis)))
                for name in vertex_materials[vi]:materials[name]=materials.get(name,0)+1
    result[rig]=dict(changed_finger_dominant_vertices=count,max_change_cm=maximum,materials=materials,forearm_distance_range_cm=[min(forearm_distances),max(forearm_distances)])
(C/'Review/finger-scope.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result,flush=True)
