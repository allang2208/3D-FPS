import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Integration/A762_Rigged_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix
report={'objects':{},'receiver_sections':[]}
for ob in s.objects:
    if ob.type!='MESH' or 'A762' not in ob.name:continue
    bone=next((g.name for g in ob.vertex_groups if g.name.startswith('WPN_')),None)
    xf=root.inverted()@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()
    v=np.array([list(xf@p.co) for p in ob.data.vertices])
    report['objects'][ob.name]={'bone':bone,'vertices':len(v),'faces':len(ob.data.polygons),'min':v.min(0).tolist(),'max':v.max(0).tolist(),'custom_normals':ob.data.has_custom_normals,'materials':[m.name for m in ob.data.materials]}
    if ob.name=='A762_Receiver':
        for y in np.arange(-.49,.121,.02):
            q=v[(abs(v[:,1]-y)<.006)]
            if len(q):report['receiver_sections'].append({'y':float(y),'xq':np.percentile(q[:,0],[2,20,50,80,98]).tolist(),'zq':np.percentile(q[:,2],[2,20,50,80,98]).tolist(),'ztop':float(q[:,2].max())})
    if ob.name in ['A762_Receiver','SM_A762_RearSight','SM_A762_FrontSight']:
        np.save(O/(ob.name+'_source_vertices.npy'),v)
(O/'source_landmarks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
