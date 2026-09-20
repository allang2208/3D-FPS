"""Focused investigation of the reported rigid-weapon deformation."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
import numpy as np
P=Path(__file__).parent;BASE=P.parent
report={}
def rot_error(a,b):
    q=a.to_quaternion().rotation_difference(b.to_quaternion())
    return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
for weapon in ('M1911','DW715'):
  receipt=json.loads((BASE/f'{weapon}-authoring.json').read_text())
  for side,entry in receipt['sides'].items():
    try:bpy.ops.wm.open_mainfile(filepath=entry['blend'])
    except RuntimeError as e:
      if 'Missing library override hierarchy root data' not in str(e):raise
    scene=bpy.context.scene;rig=bpy.data.objects['SK_M1911_Manny' if weapon=='M1911' else 'SK_DW715_Manny']
    mesh_info=[]
    for o in scene.objects:
      if o.type!='MESH' or not (o.parent==rig or any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)):continue
      groupweights={}
      for v in o.data.vertices:
        for g in v.groups:
          n=o.vertex_groups[g.group].name
          groupweights[n]=groupweights.get(n,0)+g.weight
      mesh_info.append({'name':o.name,'parent_bone':o.parent_bone,'groups':{n:round(w,3) for n,w in groupweights.items() if w>1.}})
    result={'rig_scale':list(rig.scale),'meshes':mesh_info,'clips':{}}
    weapon_bones=[b.name for b in rig.pose.bones if b.name.startswith('WPN_')]
    for kind in entry['clips']:
      action=bpy.data.actions[f'Dual_{weapon}_{side}_{kind}'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
      scene.frame_set(0);bpy.context.view_layer.update();zero={n:rig.pose.bones[n].matrix.copy() for n in weapon_bones}
      relations={n:zero['WPN_root'].inverted()@m for n,m in zero.items()}
      metric={'root_rest_scale':list(zero['WPN_root'].to_scale()),'max_scale_delta':0.,'max_shear':0.,'max_component_drift_m':0.,'max_component_turn_deg':0.,'worst_scale':None}
      for frame in range(97):
        t=frame/120.;f=t*60;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
        root=rig.pose.bones['WPN_root'].matrix.copy();sv=np.linalg.svd(np.array(root.to_3x3()),compute_uv=False)
        delta=max(abs(a-b) for a,b in zip(sv,sorted(zero['WPN_root'].to_scale(),reverse=True)))
        if delta>metric['max_scale_delta']:
          metric['max_scale_delta']=float(delta);metric['worst_scale']={'time':t,'scale':list(root.to_scale()),'singular_values':list(map(float,sv))}
        axes=[root.to_3x3().col[i].normalized() for i in range(3)]
        metric['max_shear']=max(metric['max_shear'],*(abs(axes[i].dot(axes[j])) for i,j in ((0,1),(0,2),(1,2))))
        for n in weapon_bones:
          relative=root.inverted()@rig.pose.bones[n].matrix
          metric['max_component_drift_m']=max(metric['max_component_drift_m'],(relative.translation-relations[n].translation).length)
          metric['max_component_turn_deg']=max(metric['max_component_turn_deg'],rot_error(relative,relations[n]))
      result['clips'][kind]=metric
    report[weapon+'/'+side]=result
    print('WEAPON_RIGID_SOURCE '+weapon+'/'+side+' '+json.dumps(result['clips']),flush=True)
(P/'source_diagnosis.json').write_text(json.dumps(report,indent=2))
