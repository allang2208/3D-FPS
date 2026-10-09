"""Scoped diagnosis requested by the user: native left arm through sprint.

Reuses the author equations, observes hinge transport and actual V7 skin weights.
Does not render, modify assets or launch gameplay.
"""
import bpy, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
O=Path(__file__).parent; source=O.parent/'Super90TacticalSprint20261007/author_sprint.py'
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'current'
code=(O/'Before/author_sprint.py' if label=='before' else source).read_text(encoding='utf-8-sig')
scope={'__file__':str(source)}
exec(compile(code.split("profiles={f:")[0],str(source),'exec'),scope)
rest=scope['rest']; names=scope['names']; idles=scope['idles']; pose=scope['pose']
N=('upperarm_l','lowerarm_l','hand_l')

def angle(a,b):return math.degrees(a.angle(b))
def rotation_error(a,b):
    q=a.rotation_difference(b);return math.degrees(2*math.acos(min(1.,abs(q.w))))
def metric(p,ref):
    a,e,w=[p[n].translation for n in N];a0,e0,w0=[ref[n].translation for n in N]
    u,f=e-a,w-e;u0,f0=e0-a0,w0-e0
    h=u.cross(f).normalized();h0=u0.cross(f0).normalized()
    uq=p[N[0]].to_quaternion()@ref[N[0]].to_quaternion().inverted()
    fq=p[N[1]].to_quaternion()@ref[N[1]].to_quaternion().inverted()
    wrist=rest[N[1]].to_quaternion().inverted()@rest[N[2]].to_quaternion()
    actual=p[N[1]].to_quaternion().inverted()@p[N[2]].to_quaternion()
    fd=(rest[N[2]].translation-rest[N[1]].translation).normalized()
    hand_axis=p[N[2]].to_quaternion()@rest[N[2]].to_quaternion().inverted()@fd
    return {'upper_hinge_off_deg':angle(uq@h0,h),'lower_hinge_off_deg':angle(fq@h0,h),
            'wrist_from_rest_deg':rotation_error(wrist,actual),'wrist_axis_bend_deg':angle(f,hand_axis),
            'elbow_bend_deg':angle(u,f),'reach':(w-a).length/(u0.length+f0.length),
            'shoulder_move_cm':100*(a-a0).length,'wrist':list(w),'elbow':list(e)}

# Actual mesh weight blends near the left elbow; inspect binding deformation,
# not world-space Euler angles or a synthetic one-bone approximation.
skin=[]
for ob in bpy.data.objects:
    if ob.type!='MESH' or not ob.name.startswith('Super90_V7_'):continue
    groups={g.index:g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        ws={groups[g.group]:g.weight for g in v.groups if groups[g.group] in rest and g.weight>1e-6}
        if sum(w for n,w in ws.items() if n.endswith('_l'))<.99:continue
        if ws.get('upperarm_l',0)>.03 and sum(w for n,w in ws.items() if n.startswith('lowerarm'))>.03:
            skin.append(ws)
skin_names=sorted({n for row in skin for n in row})
weights=np.array([[row.get(n,0.) for n in skin_names] for row in skin])
def skin_det(p):
    if not skin:return {}
    deforms=np.array([np.array(p[n]@rest[n].inverted())[:3,:3] for n in skin_names])
    det=np.linalg.det(np.einsum('vn,nij->vij',weights,deforms))
    return {'elbow_skin_det_p01':float(np.quantile(det,.01)),'elbow_skin_det_min':float(det.min())}

report={'label':label,'elbow_weight_samples':len(skin),'families':{},'rest':{},'runtime_tested':False}
for n in names:
    if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand')):
        report['rest'][n]={'p':list(rest[n].translation),'q':list(rest[n].to_quaternion()),'parent':scope['parents'][n]}
for family,ref in idles.items():
    report.setdefault('idle_frames',{})[family]={n:{'p':list(ref[n].translation),'scale':list(ref[n].to_scale()),'q':list(ref[n].to_quaternion())}
                                               for n in ('VM_Root','clavicle_l',*N,'lowerarm_aux_l','WPN_root')}
    rows=[];previous=None
    for i in range(37):
        t=i/36;p=pose(t,None,family);row=metric(p,ref);row.update(skin_det(p));row['progress']=t
        if previous:
            row['max_left_rotation_step_deg']=max(rotation_error(previous[n].to_quaternion(),p[n].to_quaternion()) for n in names if n.endswith('_l'))
            row['max_step_bone']=max((n for n in names if n.endswith('_l')),key=lambda n:rotation_error(previous[n].to_quaternion(),p[n].to_quaternion()))
        previous=p;rows.append(row)
    loops=[metric(pose(1.,2*math.pi*i/72,family),ref) for i in range(73)]
    keys=('upper_hinge_off_deg','lower_hinge_off_deg','wrist_from_rest_deg','wrist_axis_bend_deg','elbow_bend_deg','max_left_rotation_step_deg')
    summary={k:max(r.get(k,0.) for r in rows) for k in keys}
    if skin:summary['elbow_skin_det_min']=min(r['elbow_skin_det_min'] for r in rows)
    summary['loop_wrist_max']=max(r['wrist_from_rest_deg'] for r in loops)
    report['families'][family]={'summary':summary,'enter':rows,'loop':loops}
(O/('diagnosis_'+label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPRINT_ARM_DIAGNOSIS',json.dumps({k:v['summary'] for k,v in report['families'].items()}),flush=True)
