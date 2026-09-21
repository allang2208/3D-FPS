"""Read source coordinates needed to author replacement interfaces; no render."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refinement02/A762_Reconstructed_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix;out={}
for name in ['A762_Receiver','A762_Handguard','A762_FactoryStock']:
    ob=bpy.data.objects[name];bone=next(g.name for g in ob.vertex_groups if g.name.startswith('WPN_'))
    xf=root.inverted()@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()
    v=np.array([tuple(xf@p.co) for p in ob.data.vertices]);np.save(O/(name+'.npy'),v)
    result={'min':v.min(0).tolist(),'max':v.max(0).tolist(),'sections':[]}
    for y in [-.365,-.35,-.33,-.30,-.25,-.20,-.17,-.10,-.04,0,.03,.045,.06,.08,.10,.112,.122,.13]:
        q=v[abs(v[:,1]-y)<.0025]
        if len(q):
            upper=q[q[:,2]>np.percentile(q[:,2],65)]
            result['sections'].append({'y':y,'x':np.percentile(q[:,0],[1,50,99]).tolist(),'z':np.percentile(q[:,2],[1,50,99]).tolist(),'upper_x':np.percentile(upper[:,0],[1,50,99]).tolist()})
    out[name]=result
(O/'source_coordinates.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2),flush=True)
