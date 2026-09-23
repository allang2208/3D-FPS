"""Bake bilateral thrust elbow support; preserve all joint origins and grips."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from diagnose_elbows import matrix,pack,rebuild,seam,PRIOR,ROOT
import elbow_support as solver
STATIONS=json.loads((ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/authoring.json').read_text())['skin_stations']
EDIT=[n+'_'+s for s in ('l','r') for n in ('upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
if __name__=='__main__':
    diagnosis=json.loads((P/'diagnosis.json').read_text());report={}
    for variant in ('Standard','LongGrip'):
        d=json.loads((PRIOR/variant/'source.json').read_text());v1=json.loads((PRIOR/variant/'Thrust_patch.json').read_text())
        rest={n:matrix(t) for n,t in d['rest'].items()};info=d['clips']['Thrust'];state={};previous={};rows=[];metrics=[];last_delta={};max_step=(0,None,0)
        for row,correction in zip(info['samples'],v1['samples']):
            _,current=rebuild(row,correction,d['parents']);fixed={n:m.copy() for n,m in current.items()}
            t=row['seconds'];weight=solver.smooth(t/.12)*solver.smooth((info['seconds']-t)/.12)
            for s in ('l','r'):fixed.update(solver.support_elbow(current,rest,STATIONS,s,state,weight))
            for n in EDIT:
                delta=current[n].to_quaternion().inverted()@fixed[n].to_quaternion()
                if n in last_delta:
                    step=math.degrees(2*math.acos(min(1,abs(delta.dot(last_delta[n])))))
                    if step>max_step[0]:max_step=(step,n,t)
                last_delta[n]=delta
            keys={}
            for n in EDIT:
                parent=d['parents'][n];local=fixed[parent].inverted()@fixed[n];p,q,scale=local.decompose()
                # Keep the source scale keys; this correction only authors rotations.
                scale=(current[parent].inverted()@current[n]).decompose()[2]
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n]=q.copy();keys[n]={'p':list(p),'q':list(q),'s':list(scale)}
            rows.append({'seconds':t,'bones':keys})
            metrics.append({'seconds':t,**{s:{'source_seam_deg':seam(current,rest,s),'fixed_seam_deg':seam(fixed,rest,s)} for s in ('l','r')}})
        patch={'revision':'ThrustElbowSupportV1','asset':diagnosis[variant]['asset'],'sha256':diagnosis[variant]['current_sha256'],
          'intervals':info['intervals'],'seconds':info['seconds'],'edited_bones':EDIT,'samples':rows}
        out=P/variant;out.mkdir(exist_ok=True)
        (out/'Thrust_patch.json').write_text(json.dumps(patch,separators=(',',':')))
        report[variant]={'rows':metrics,'frames':len(rows),'joint_origins':'source','hand_fingers':'source','distal_twist':'source','maximum_correction_step_deg_bone_time':max_step}
        print('CORRECTION_CONTINUITY',variant,max_step)
        for t in (.12,.4,.58,.8,1.12):print(variant,min(metrics,key=lambda r:abs(r['seconds']-t)))
    (P/'authoring.json').write_text(json.dumps(report,indent=2))
