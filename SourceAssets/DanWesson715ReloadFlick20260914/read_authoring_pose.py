"""Read the existing source poses and skin anatomy needed for this correction."""
import bpy,json
from pathlib import Path
from mathutils import Vector
import numpy as np
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715SingleLoad20260914/DanWesson715_SingleLoad_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
r=bpy.data.objects['SK_DW715_Manny'];s=bpy.context.scene
a=bpy.data.actions['DW715V2_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
G=r.pose.bones['WPN_root'].matrix.copy();H=r.pose.bones['hand_l'].matrix.copy()
def mat(m):return [list(row) for row in m]
data={'idle_gun_world':mat(G),'left_in_gun':mat(G.inverted()@H),'right_in_gun':mat(G.inverted()@r.pose.bones['hand_r'].matrix),'bones':{},'source_reload':{}}
for b in r.data.bones:
    if b.name.startswith(('thumb','index','middle','ring','pinky')) and b.name.endswith('_l'):
        p=r.pose.bones[b.name]
        data['bones'][b.name]={'rest_hand':mat(r.data.bones['hand_l'].matrix_local.inverted()@b.matrix_local),'idle_hand':mat(H.inverted()@p.matrix),'length':b.length}
mesh=bpy.data.objects['SK_Manny_Arms_Export']
to_rig=r.matrix_world.inverted()@mesh.matrix_world
for family in ['thumb','index','middle','ring','pinky']:
    name=family+'_03_l';b=r.data.bones[name];group=mesh.vertex_groups.get(name)
    points=[to_rig@v.co for v in mesh.data.vertices if group and any(g.group==group.index and g.weight>.45 for g in v.groups)]
    axis=(b.matrix_local.translation-r.data.bones[family+'_02_l'].matrix_local.translation).normalized()
    projections=np.array([(v-b.matrix_local.translation).dot(axis) for v in points])
    cap=[v for v,projection in zip(points,projections) if projection>=float(np.quantile(projections,.88))]
    tip=sum(cap,Vector())/len(cap)
    data['bones'][name]['skin_tip_local']=list(b.matrix_local.inverted()@tip)
    data['bones'][name]['skin_tip_hand']=list(r.data.bones['hand_l'].matrix_local.inverted()@tip)
    print('SKIN_TIP',family,data['bones'][name]['skin_tip_hand'],flush=True)
for kind in ['DW715_Single_0_6','DW715V2_reload']:
    a=bpy.data.actions[kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    frames={}
    for t in [0,.22,.48,.55,.78,1.11,1.46]:
        f=t*60;s.frame_set(int(f),subframe=f%1)
        g=r.pose.bones['WPN_root'].matrix.copy()
        frames[str(t)]={n:mat(g.inverted()@r.pose.bones[n].matrix) for n in ['hand_l','WPN_Crane','WPN_Cylinder','WPN_Case_0']}
    data['source_reload'][kind]=frames
(O/'authoring-inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('IDLE_GUN_WORLD',mat(G),flush=True)
for side in ['l','r']:
    print('HAND_LOCAL',side,data['left_in_gun' if side=='l' else 'right_in_gun'],flush=True)
for n,b in data['bones'].items():
    if 'metacarpal' not in n:print('FINGER',n,'rest',[round(row[3],5) for row in b['rest_hand'][:3]],'idle',[round(row[3],5) for row in b['idle_hand'][:3]],'length',round(b['length'],5),flush=True)
