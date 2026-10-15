"""Read the current shoulder-cut geometry for animation positioning, no render."""
import bpy,json,math
import numpy as np
from pathlib import Path
from collections import Counter,defaultdict
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ComboV1/Warhammer_Combo_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];skin=bpy.data.objects['Warhammer_BareArmsV7']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
vertices=[rig.matrix_world.inverted()@skin.matrix_world@v.co for v in skin.data.vertices]
groups={g.index:g.name for g in skin.vertex_groups}
weights=[{groups[g.group]:g.weight for g in v.groups if g.weight>1e-6} for v in skin.data.vertices]
weld={};ids=[];rep={}
for i,p in enumerate(vertices):
    key=tuple(round(v,5) for v in p)
    if key not in weld:weld[key]=len(weld)
    ids.append(weld[key]);rep[weld[key]]=i
edges=Counter()
for poly in skin.data.polygons:
    face=[ids[i] for i in poly.vertices]
    for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))]+=1
adj=defaultdict(set)
for (a,b),count in edges.items():
    if count==1:adj[a].add(b);adj[b].add(a)
remaining=set(adj);rings=[]
while remaining:
    stack=[remaining.pop()];ring=[]
    while stack:
        i=stack.pop();ring.append(rep[i])
        for j in adj[i]:
            if j in remaining:remaining.remove(j);stack.append(j)
    gw=Counter()
    for i in ring:gw.update(weights[i])
    if len(ring)>8 and any('upperarm' in n for n,_ in gw.most_common(3)):
        rings.append({'vertices':ring,'weights':gw.most_common(5)})
report={'rings':rings,'rest_joints':{n:list(rest[n].translation) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')},'poses':{}}
for name in ('A_Warhammer_Slash1','A_Warhammer_Slash2','A_RusticPickaxe_Swing','A_RusticPickaxe_Idle'):
    action=bpy.data.actions.get(name)
    if not action:continue
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    fps=300 if name=='A_RusticPickaxe_Swing' else 150
    samples=[]
    frames=[0,round(.13*fps),round(.188*fps),round(.24*fps),round(.40*fps),round(.60*fps)] if 'Idle' not in name else [0]
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        pose={b.name:b.matrix.copy() for b in rig.pose.bones}
        row={'frame':frame,'seconds':frame/fps,'joints':{n:list(pose[n].translation) for n in report['rest_joints']},'cuts':[]}
        for ring in rings:
            ps=[]
            for i in ring['vertices']:
                total=sum(weights[i].values())
                p=sum((np.array(pose[n]@rest[n].inverted()@vertices[i])*w/total for n,w in weights[i].items()))
                ps.append(p)
            arr=np.array(ps);tv=math.tan(math.radians(75/2));x,d,z=arr.T
            row['cuts'].append({'min':arr.min(axis=0).tolist(),'max':arr.max(axis=0).tolist(),
                'inside_vertices':int(np.count_nonzero((d>.01)&(abs(x)<tv*16/9*d)&(abs(z)<tv*d)))})
        samples.append(row)
    report['poses'][name]={'frame_range':list(action.frame_range),'samples':samples}
(P/'source_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'rings':[(len(r['vertices']),r['weights']) for r in rings],
    'poses':{n:[{'s':v['seconds'],'cuts':v['cuts']} for v in a['samples']] for n,a in report['poses'].items()}}))
