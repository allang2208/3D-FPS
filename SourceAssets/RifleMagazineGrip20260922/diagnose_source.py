import bpy, json, math
from pathlib import Path
from collections import Counter
from mathutils import Vector

O=Path(__file__).parent; S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'AKMReloadPolish20260911/base/A_AKM_reload.blend'))
r=bpy.data.objects['SK_M4_Infima']; skin=bpy.data.objects['SK_Manny_Arms_Export']; s=bpy.context.scene
gn={g.index:g.name for g in skin.vertex_groups}
digits=('thumb','index','middle','ring','pinky')
stats=Counter(); mixtures=Counter()
for v in skin.data.vertices:
    weights={gn[g.group]:g.weight for g in v.groups if g.weight>1e-5}
    ds={n.split('_')[0] for n in weights if n.endswith('_l') and n.startswith(digits)}
    if not ds:continue
    stats['left_digit_vertices']+=1
    if abs(sum(weights.values())-1)>.002:stats['not_normalized']+=1
    if len(ds)>1:
        stats['multiple_digit_families']+=1
        mixtures['+'.join(sorted(ds))]+=1
    stats['max_influences']=max(stats['max_influences'],len(weights))
report={'weights':dict(stats),'mixed_digit_families':dict(mixtures),'fps':s.render.fps,'range':[s.frame_start,s.frame_end],'action':r.animation_data.action.name,'rest':{},'frames':{}}
names=['hand_l']+[b.name for b in r.data.bones if b.name.endswith('_l') and b.name.startswith(digits)]
for n in names:
    b=r.data.bones[n]
    report['rest'][n]={'parent':b.parent.name,'position':list(b.matrix_local.translation),'matrix':[list(row) for row in b.matrix_local]}
for f in [60,90,105,130,148,178,200,220,280,400]:
    s.frame_set(f);bpy.context.view_layer.update();mag=r.pose.bones['WPN_SOCKET_Magazine'].matrix.copy()
    row={}
    for n in names:
        b=r.pose.bones[n];basis=b.matrix_basis.to_quaternion()
        row[n]={'position_in_mag':list(mag.inverted()@b.matrix.translation),'basis':list(basis),'matrix':[list(x) for x in b.matrix]}
    report['frames'][f]=row
(O/'source_diagnosis.json').write_text(json.dumps(report,indent=2))
print('SOURCE_HAND_WEIGHTS',dict(stats),dict(mixtures),flush=True)
