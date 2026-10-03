"""Requested offline diagnosis of the accepted M10 walking and turning legs."""
from pathlib import Path
import json,math
import bpy,numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'SurfaceRigV5'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Delivery/M10_SurfaceRigV5_Editable.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
cfg=json.loads((BASE/'rig_definition.json').read_text(encoding='utf8'))
data=np.load(BASE/'surface_rig_data.npz');names=list(data['bone_names'])
verts=data['vertices']+data['displacement'];indices=data['bone_indices'];weights=data['weights']
rest={b.name:b.matrix_local.inverted() for b in rig.data.bones}
selected={}
for leg in cfg['legs']:
    prefix=leg['region'];ids=[names.index(prefix+s) for s in ('_foot','_toes_inner','_toes_outer')]
    mask=(weights*np.isin(indices,ids)).sum(axis=1)>.65
    ids=np.flatnonzero(mask);ids=ids[::max(1,len(ids)//400)]
    selected[prefix]=ids
report={'scope':'source locomotion only; no UE game or render','clips':{}}
for role in ('Walk','CurveLeft','CurveRight','PivotLeft','PivotRight'):
    action=bpy.data.actions['M10_'+role+'_V5'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    rows={leg['region']:{'reach':[],'sole_z_cm':[],'ankle_z_cm':[],'stance_sole_z_cm':[]} for leg in cfg['legs']}
    for frame in range(1,37):
        scene.frame_set(frame)
        matrices=np.array([rig.pose.bones[str(n)].matrix@rest[str(n)] for n in names])
        for leg in cfg['legs']:
            key=leg['region'];row=rows[key];ids=selected[key];points=verts[ids]
            posed=np.zeros_like(points)
            for slot in range(4):
                m=matrices[indices[ids,slot]]
                posed+=weights[ids,slot,None]*(np.einsum('nij,nj->ni',m[:,:3,:3],points)+m[:,:3,3])
            a,b,c=[rig.pose.bones[n].matrix.translation for n in leg['bones']]
            row['reach'].append((c-a).length/((b-a).length+(c-b).length))
            row['sole_z_cm'].append(float(posed[:,2].min()*100));row['ankle_z_cm'].append(c.z*100)
            phase=((frame-1)/36+[0,.5,.25,.75][leg['pair']-1]+(.5 if leg['side']=='R' else 0))%1
            if phase<(.65 if role=='Walk' else .75):row['stance_sole_z_cm'].append(row['sole_z_cm'][-1])
    report['clips'][role]={k:{'max_extension_fraction':max(v['reach']),
        'frames_at_98pct_extension':sum(x>=.9799 for x in v['reach']),
        'sampled_sole_z_min_cm':min(v['sole_z_cm']),'stance_sole_z_max_cm':max(v['stance_sole_z_cm'])} for k,v in rows.items()}
(ROOT/'source_locomotion_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M10_LOCOMOTION_DIAGNOSIS',json.dumps({role:{'near_straight_leg_frames':sum(v['frames_at_98pct_extension'] for v in rows.values()),'lowest_sample_cm':min(v['sampled_sole_z_min_cm'] for v in rows.values()),'highest_stance_sample_cm':max(v['stance_sole_z_max_cm'] for v in rows.values())} for role,rows in report['clips'].items()}),flush=True)
