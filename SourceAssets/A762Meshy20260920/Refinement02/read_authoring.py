import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refinement01/A762_Refined_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix;report={}
for name in ['A762_Magazine','A762_Receiver','A762_Handguard']:
    ob=bpy.data.objects[name];bone=next(g.name for g in ob.vertex_groups if g.name.startswith('WPN_'));xf=root.inverted()@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()
    v=np.array([tuple(xf@p.co) for p in ob.data.vertices]);np.save(O/(name+'.npy'),v)
    entry={'bone':bone,'min':v.min(0).tolist(),'max':v.max(0).tolist()}
    if name=='A762_Magazine':
        entry['slices']=[]
        for z in np.arange(-.135,.036,.008):
            q=v[abs(v[:,2]-z)<.003]
            if len(q):entry['slices'].append({'z':float(z),'y':np.percentile(q[:,1],[1,10,50,90,99]).tolist(),'x':np.percentile(q[:,0],[1,50,99]).tolist()})
    report[name]=entry
(O/'landmarks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
