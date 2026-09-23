"""Compare the saved V1 track patch with its exact pre-V1 source pose."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[1];PRIOR=ROOT/'SourceAssets/MeleeArmOpening20260923'
def matrix(t):return Matrix.LocRotScale(Vector(t['p']),Quaternion(t['q']),Vector(t['s']))
def pack(m):
    p,q,s=m.decompose();return {'p':list(p),'q':list(q),'s':list(s)}
def rebuild(row,patch,parents):
    original={n:matrix(t) for n,t in row['world'].items()};current={}
    for n,parent in parents.items():
        local=matrix(patch['bones'][n]) if n in patch['bones'] else (original[parent].inverted()@original[n] if parent in original else original[n])
        current[n]=current[parent]@local if parent in current else local
    return original,current
def seam(pose,rest,side):
    U,F,H=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    axis=(pose[H].translation-pose[F].translation).normalized()
    rest_axis=(rest[H].translation-rest[F].translation).normalized()
    up=pose[U].to_quaternion()@rest[U].to_quaternion().inverted()
    fore=pose[F].to_quaternion()@rest[F].to_quaternion().inverted()
    hinge=(up@rest_axis).rotation_difference(axis)@up
    q=fore@hinge.inverted()
    return math.degrees((2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)+math.pi)%(2*math.pi)-math.pi)
def elbow(pose,side):
    a,e,h=[pose[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
    return math.degrees((a-e).angle(h-e))
if __name__=='__main__':
    receipt=json.loads((PRIOR/'install_receipt.json').read_text());report={}
    for variant in ('Standard','LongGrip'):
        d=json.loads((PRIOR/variant/'source.json').read_text());patch=json.loads((PRIOR/variant/'Thrust_patch.json').read_text())
        installed=receipt['saved'][variant+'/Thrust_patch'];disk=ROOT/'Content'/(installed['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=installed['saved_sha256']:raise RuntimeError('Installed thrust changed: '+variant)
        rest={n:matrix(v) for n,v in d['rest'].items()};rows=[]
        for row,correction in zip(d['clips']['Thrust']['samples'],patch['samples']):
            original,current=rebuild(row,correction,d['parents']);r={'time':row['seconds']}
            for side in ('l','r'):
                r[side]={'before_seam_deg':seam(original,rest,side),'v1_seam_deg':seam(current,rest,side),
                    'before_elbow_deg':elbow(original,side),'v1_elbow_deg':elbow(current,side)}
            rows.append(r)
        report[variant]={'asset':installed['asset'],'current_sha256':installed['saved_sha256'],'rows':rows}
        for t in (.4,.48,.54,.58,.64,.8):
            r=min(rows,key=lambda r:abs(r['time']-t));print(variant,round(r['time'],4),json.dumps(r))
    (P/'diagnosis.json').write_text(json.dumps(report,indent=2))
