"""Fit camera-hidden shoulder openings, preserving the held group and timing.

Surface fitting is part of animation production. No render or game is run.
"""
import json,math,sys,itertools
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from mesh_source import matrix,load_geometry

TV=math.tan(math.radians(82/2));TH=TV*16/9;MARGIN=1.5
ONE=Vector((1,1,1))
EDIT=[n+'_'+s for s in ('l','r') for n in ('clavicle','upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]+['WPN_root']
def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(10-15*t+6*t*t)
def serialize(m):
    p,q,s=m.decompose();return {'p':list(p),'q':list(q),'s':list(s)}
def fit(source,parents,weight,profile):
    pose={n:m.copy() for n,m in source.items()}
    back,down,out=profile;arms={};retreat=0.
    for side in ('l','r'):
        a,e,h=[source[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
        l1,l2=(e-a).length,(h-e).length
        shift=Vector(((-1 if side=='l' else 1)*out,back,-down))*weight
        shoulder=a+shift;distance=h-shoulder;reach=(l1+l2)*.985
        # Preserve one shared hand/weapon displacement when moving the roots
        # back would otherwise force a stretched or completely locked elbow.
        retreat=max(retreat,-distance.y-math.sqrt(max(.01,reach*reach-distance.x**2-distance.z**2)))
        arms[side]=(a,e,h,shoulder,l1,l2)
    delta=Vector((0,max(0.,retreat),0))
    for side,(a,e,h,shoulder,l1,l2) in arms.items():
        wrist=h+delta;d=wrist-shoulder;length=d.length;axis=d.normalized()
        pole=e-a;pole=(pole-axis*pole.dot(axis)).normalized()
        along=(l1*l1-l2*l2+length*length)/(2*length)
        elbow=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
        for stem,old_a,old_b,new_a,new_b in [('upperarm',a,e,shoulder,elbow),('lowerarm',e,h,elbow,wrist)]:
            turn=(old_b-old_a).rotation_difference(new_b-new_a)
            transform=Matrix.Translation(new_a)@turn.to_matrix().to_4x4()@Matrix.Translation(-old_a)
            for name in (stem+'_'+side,stem+'_twist_01_'+side,stem+'_twist_02_'+side):
                pose[name]=transform@source[name]
        pose['clavicle_'+side].translation+=shoulder-a
    moved={'hand_l','hand_r','WPN_root'}
    for n in source:
        if n in moved or parents.get(n) in moved:
            pose[n].translation+=delta;moved.add(n)
    return pose,float(delta.y)

class Surface:
    def __init__(self,geometry,rest):
        self.rings=[]
        for ring in geometry['boundaries']:
            if not any('upperarm' in name for name,_ in ring['weights']):continue
            ids=ring['vertices'];points=np.array([[*geometry['vertices'][i],1] for i in ids]);groups={}
            for n in {n for i in ids for n in geometry['weights'][i]}:
                weights=np.array([geometry['weights'][i].get(n,0) for i in ids])
                local=points@np.array(rest[n].inverted()).T
                groups[n]=(local,weights)
            self.rings.append(groups)
    def error(self,pose):
        errors=[]
        for ring in self.rings:
            p=sum((local@np.array(pose[n]).T)[:,:3]*w[:,None] for n,(local,w) in ring.items())
            x,d,z=p[:,0],-p[:,1],p[:,2]
            planes=[d,TH*d-x,TH*d+x,TV*d+z,TV*d-z]
            errors.append(min(float(np.max(v))+MARGIN for v in planes))
        return max(errors)

manifest={'revision':'MeleeArmOpeningV1','frustum_vertical_degrees':82,'aspect':16/9,'opening_margin_cm':MARGIN,
          'scope':'Standard and LongGrip Thrust, Overhead, SprintOverhead','gameplay_tested':False,'rendered':False,'clips':{}}
for variant in ('Standard','LongGrip'):
    out=P/variant;data=json.loads((out/'source.json').read_text());geometry=json.loads((out/'geometry.json').read_text())
    rest={n:matrix(v) for n,v in data['rest'].items()};surface=Surface(geometry,rest);parents=data['parents']
    for clip in ('Thrust','Overhead','SprintOverhead'):
        info=data['clips'][clip];source=[{n:matrix(v) for n,v in r['world'].items()} for r in info['samples']]
        times=[r['seconds'] for r in info['samples']]
        begin=.97 if clip=='SprintOverhead' else 0.
        visible=[t for t,p in zip(times,source) if t>=begin and surface.error(p)>0]
        if visible:
            first,last=min(visible),max(visible)
            start=max(begin,first-.16);finish=min(info['seconds'],last+.20)
            weights=[smooth((t-start)/max(.001,first-start))*smooth((finish-t)/max(.001,finish-last)) for t in times]
        else:weights=[0.]*len(times);first=last=0.
        # Choose a small, fixed correction per motion, rather than a per-frame
        # pole switch. Smoothly enter/leave it around the exposed interval.
        candidates=sorted(itertools.product((0,2,4,6,8),(0,2,4),(0,2,4)),key=lambda v:v[0]**2+1.5*v[1]**2+2*v[2]**2)
        best=None
        active=[i for i,w in enumerate(weights) if w>0]
        for profile in candidates:
            worst=-100.;max_retreat=0.
            for i in active:
                posed,retreat=fit(source[i],parents,weights[i],profile)
                worst=max(worst,surface.error(posed));max_retreat=max(max_retreat,retreat)
                if worst>0. or max_retreat>10.:break
            if worst<=0. and max_retreat<=10.:
                best=profile;break
        if best is None:
            # Keep a modest pose correction for a later hidden-geometry layer;
            # do not shorten the attack drastically to hide a mesh cut.
            best=(4,2,0)
        rows=[];previous={};worst=-100.;max_retreat=0.;max_shift=0.
        for t,w,original in zip(times,weights,source):
            posed,retreat=fit(original,parents,w,best) if w>0 else (original,0.)
            worst=max(worst,surface.error(posed) if t>=begin else -100.);max_retreat=max(max_retreat,retreat)
            keys={}
            for n in EDIT:
                local=posed[parents[n]].inverted()@posed[n];p,q,s=local.decompose()
                # Retain original scales; this patch only transports segments.
                s=(original[parents[n]].inverted()@original[n]).to_scale()
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n]=q.copy();keys[n]={'p':list(p),'q':list(q),'s':list(s)}
            rows.append({'seconds':t,'bones':keys})
        patch={k:info[k] for k in ('asset','intervals','seconds','sha256')}
        patch.update({'revision':manifest['revision'],'edited_bones':EDIT,'samples':rows})
        (out/(clip+'_patch.json')).write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
        record={'profile_back_down_out_cm':best,'exposed_interval':[first,last],
            'max_held_group_retreat_cm':max_retreat,'remaining_opening_constraint_cm':worst,
            'needs_geometry_extension':worst>0,'asset':info['asset'],'intervals':info['intervals'],'seconds':info['seconds']}
        manifest['clips'][variant+'/'+clip]=record
        print('SHOULDER_POSE_AUTHORED',variant,clip,json.dumps(record),flush=True)
(P/'authoring.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
