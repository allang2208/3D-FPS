"""Extract native joint and surface inputs for authoring the rectangular grasp."""
from pathlib import Path
import json
O=Path(__file__).parent
author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
source=(O/'Before/Source/author_speedloader.py').read_text(encoding='utf-8').split('def arm(')[0]
source=source.replace("idles={'base':idle}", """eval_base={}
for n in names:eval_base[n]=eval_base.get(parents[n],I)@uemat(D['clips']['idle']['samples'][0]['local'][n])
root=next(n for n in names if parents[n] is None)
evaluation_to_author=idle[root]@(Ci@eval_base[root]@Ki[root]).inverted()
idles={'base':idle}""")
source=source.replace('n:Ci@world[n]@Ki[n]', 'n:evaluation_to_author@Ci@world[n]@Ki[n]')
g={'__file__':str(author)}
exec(compile(source,str(author),'exec'),g)
out={'hand_in_handle':[list(r) for r in g['hand_in_handle']], 'joints':{},'objects':[]}
for n in g['finger_names']['l']+['hand_l','lowerarm_l','upperarm_l']:
    b=g['rig'].data.bones[n]
    world=g['grasp'][n]
    out['joints'][n]={'parent':g['parents'][n], 'position':list(g['grasp_frame'].inverted()@world.translation),
        'tail':list(g['grasp_frame'].inverted()@world@b.matrix_local.inverted()@b.tail_local),'length':b.length}
for ob in g['bpy'].data.objects:
    if ob.type=='MESH':out['objects'].append({'name':ob.name,'vertices':len(ob.data.vertices),'groups':[v.name for v in ob.vertex_groups][:8]})
(O/'grasp_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
ob=g['bpy'].data.objects['Super90_V7_M4_BareArmsV6']
mesh=ob.data
vertices=[]
for v in mesh.vertices:
    weights={ob.vertex_groups[w.group].name:w.weight for w in v.groups if w.weight>1e-5}
    if sum(w for n,w in weights.items() if n.endswith('_l') and (n.startswith(('thumb','index','middle','ring','pinky')) or n=='hand_l'))<.999:continue
    vertices.append({'id':v.index,'p':list(ob.matrix_world@v.co),'weights':weights})
skin={'names':['hand_l']+g['finger_names']['l'],'parents':g['parents'],
      'rest':{n:[list(r) for r in m] for n,m in g['rest'].items()},
      'grasp':{n:[list(r) for r in m] for n,m in g['grasp'].items()},
      'frame':[list(r) for r in g['grasp_frame']], 'vertices':vertices}
(O/'grasp_skin_inputs.json').write_text(json.dumps(skin,separators=(',',':')),encoding='utf-8')
print('NATIVE_GRASP_INPUTS',len(vertices))
