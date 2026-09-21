"""Read the actual stock attachment surfaces for local reconstruction."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refinement03/A762_ADS_Surfaces_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
out={}
for name in ['A762_FactoryStock','A762_Stock_UpperTube','A762_Stock_LowerTube']:
    ob=bpy.data.objects[name];bone=next(g.name for g in ob.vertex_groups if g.name.startswith('WPN_'))
    xf=root.inverted()@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()
    v=np.array([tuple(xf@p.co) for p in ob.data.vertices]);np.save(O/(name+'.npy'),v)
    o={'bone':bone,'min':v.min(0).tolist(),'max':v.max(0).tolist(),'sections':[]}
    for z in np.arange(-.080,.109,.010):
        q=v[abs(v[:,2]-z)<.0015]
        if len(q):o['sections'].append({'z':round(float(z),4),'x':np.percentile(q[:,0],[1,50,99]).tolist(),'y':np.percentile(q[:,1],[1,15,50,85,99]).tolist()})
    out[name]=o
(O/'stock_interfaces.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2),flush=True)
