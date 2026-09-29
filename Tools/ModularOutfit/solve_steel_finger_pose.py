"""Bake bounded armor-only pinky corrections against native grip/reload poses.

No source animation is edited. Outputs small local rotation curves consumed
after the existing runtime pose blend, only while steel gauntlets are worn.
"""
import sys,math,itertools
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P,read,write
from steel_motion_contacts import posed_groups,intersections
from diagnose_steel_grip import matrix,tree
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT=R/'ArticulationSolve20260928'
NAMES=[f'pinky_{i:02d}_{s}' for s in ('r','l') for i in (1,2,3)]
LEFT_PREFIXES=('hand_','thumb_','index_','middle_','ring_','pinky_')

def rotation(axis,degrees):
    axis=np.asarray(axis);axis/=np.linalg.norm(axis);x,y,z=axis
    skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    t=math.radians(degrees);return np.eye(3)+math.sin(t)*skew+(1-math.cos(t))*(skew@skew)

def oriented_faces(d):
    p=np.asarray(d['positions']);t=np.asarray(d['triangles']).copy();v=p[t]
    cross=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);normal=np.asarray(d['normals']).mean(1)
    flip=np.einsum('ij,ij->i',cross,normal)<0;t[flip]=t[flip][:,::-1]
    return t

class Case:
    def __init__(self,d,parts,sample,axes,deform,faces):
        self.axes=axes;self.pose={n:matrix(b) for n,b in sample['bones'].items()}
        self.left=[n for n in self.pose if n.endswith('_l') and n.startswith(LEFT_PREFIXES)]
        self.changed=list(dict.fromkeys(NAMES+self.left))
        self.rest={n:np.linalg.inv(matrix(d['bones'][n])) for n in self.changed}
        self.positions=np.asarray(d['positions']);self.base=deform(sample['bones']);self.faces=faces
        skin=faces[np.asarray(d['triangle_materials'])==0]
        moved=np.array([sum(w.get(n,0.) for n in self.changed)>.001 for w in d['weights']])
        fixed_skin=skin[~moved[skin].any(1)];self.moving_skin=skin[moved[skin].any(1)]
        fixed_parts=[p for p in parts if p['kind']=='steel_plate' and p['bone'] not in self.changed]
        fixed_steel=np.concatenate([faces[p['first_triangle']:p['first_triangle']+p['triangles']] for p in fixed_parts])
        moving_parts=[p for p in parts if p['kind']=='steel_plate' and p['bone'] in self.left and p['bone'] not in NAMES]
        self.moving_skin=np.concatenate([self.moving_skin]+[faces[p['first_triangle']:p['first_triangle']+p['triangles']] for p in moving_parts])
        self.static_faces=np.concatenate([fixed_skin,fixed_steel])
        self.static=tree(self.base,self.static_faces)
        self.groups=[]
        for n in self.changed:
            ids=np.flatnonzero(moved & np.array([w.get(n,0.)>0 for w in d['weights']]))
            weights=np.array([d['weights'][i][n] for i in ids])
            self.groups.append((n,ids,weights))
        self.fixed=self.base.copy()
        for n,ids,weights in self.groups:
            tr=self.pose[n]@self.rest[n]
            self.fixed[ids]-=(self.positions[ids]@tr[:3,:3].T+tr[:3,3])*weights[:,None]
        self.plate_faces=[]
        for p in parts:
            if p['kind']!='steel_plate' or p['bone'] not in NAMES:continue
            self.plate_faces.append(faces[p['first_triangle']:p['first_triangle']+p['triangles']])
        self.original_tips=np.array([self.pose[f'pinky_03_{s}'][:3,3] for s in ('r','l')])
        self.last=None

    def transforms(self,values):
        basis=self.pose['hand_l'][:3,:3].copy();basis/=np.linalg.norm(basis,axis=0)
        offset=basis@np.asarray(values[8:11]);base=dict(self.pose);current={}
        for n in self.left:
            base[n]=self.pose[n].copy();base[n][:3,3]+=offset;current[n]=base[n]
        for side_index,side in enumerate(('r','l')):
            v=values[side_index*4:side_index*4+4]
            for segment in (1,2,3):
                n=f'pinky_{segment:02d}_{side}';delta=np.eye(4)
                if segment==1:
                    delta[:3,:3]=rotation(self.axes[n]['spread'],v[0])@rotation(self.axes[n]['bend'],v[1])
                    current[n]=base[n]@delta
                else:
                    parent=f'pinky_{segment-1:02d}_{side}'
                    delta[:3,:3]=rotation(self.axes[n]['bend'],v[segment])
                    current[n]=current[parent]@np.linalg.inv(base[parent])@base[n]@delta
        return current

    def objective(self,values):
        current=self.transforms(values);p=self.fixed.copy()
        for n,ids,weights in self.groups:
            tr=current[n]@self.rest[n]
            p[ids]+=(self.positions[ids]@tr[:3,:3].T+tr[:3,3])*weights[:,None]
        dynamic=tree(p,self.moving_skin)
        penalty=0.;count=0;worst=0.
        # Actual triangle crossings avoid signed-distance false positives at
        # open skin boundaries and on the far side of a thin armor plate.
        for faces in self.plate_faces:
            plate=tree(p,faces)
            for other_faces,obstacle in ((self.static_faces,self.static),(self.moving_skin,dynamic)):
                ids,depths=intersections(p,faces,other_faces,plate,obstacle)
                if len(ids):
                    penalty+=float(np.square(depths*.1).sum())+len(ids)*.00002
                    worst=max(worst,float(depths.max()));count+=len(ids)
        travel=np.linalg.norm(np.array([current[f'pinky_03_{s}'][:3,3] for s in ('r','l')])-self.original_tips,axis=1)
        shift=float(np.linalg.norm(values[8:11]))
        value=penalty*35.+(worst*.1)**2*300.+float(np.square(values[:8]).sum())*.00005+shift*shift*.05+max(shift-.3,0)**2*1000+float(np.square(np.maximum(travel-.45,0)).sum())*90.
        self.last=dict(cost=float(value),crossing_pairs=count,max_plane_cross_mm=worst,max_tip_root_shift_cm=float(travel.max()),left_hand_shift_cm=shift)
        return value

def solve(case,initial):
    best=np.asarray(initial,float).copy();score=case.objective(best)
    initial_result=dict(case.last)
    zero=np.zeros(11);zero_score=case.objective(zero)
    before=dict(case.last)
    if before['crossing_pairs']==0:return zero,before,before
    if initial_result['crossing_pairs']==0:return best,before,initial_result
    if zero_score<score:best=zero;score=zero_score
    bounds=np.array([8.,8.,10.,10.]*2+[.3]*3)
    # Search a small support-hand clearance before asking finger joints to
    # contort around the other hand. This represents the added glove thickness.
    for direction in itertools.product((-1.,0.,1.),repeat=3):
        direction=np.asarray(direction)
        if not np.any(direction):continue
        candidate=zero.copy();candidate[8:11]=direction/np.linalg.norm(direction)*.25
        value=case.objective(candidate)
        if value<score:score=value;best=candidate
    for side in (0,1):
        for seed in ((0,4,4,4),(0,-4,-4,-4),(4,0,0,0),(-4,0,0,0)):
            candidate=best.copy();candidate[side*4:side*4+4]=seed
            value=case.objective(candidate)
            if value<score:score=value;best=candidate
    for step in (4.,2.,1.,.5):
        for sweep in range(3):
            changed=False
            for axis in range(11):
                for sign in (-1,1):
                    candidate=best.copy();increment=step if axis<8 else step*.02
                    candidate[axis]=np.clip(candidate[axis]+increment*sign,-bounds[axis],bounds[axis])
                    shift_length=np.linalg.norm(candidate[8:11])
                    if shift_length>.3:candidate[8:11]*=.3/shift_length
                    value=case.objective(candidate)
                    if value<score:score=value;best=candidate;changed=True
            if not changed:break
    case.objective(best)
    return best,before,dict(case.last)

def main():
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    master=read(R/'Master/M4.json');parts=read(R/'parts.json')
    output=dict(version=1,equipment='ue_steel_gauntlets',bone_names=NAMES,clips=[])
    previous_output={c['asset']:c for c in read(OUT/'pinky-pose-corrections.json')['clips']} if '--refine' in sys.argv else {}
    for profile in ('M4','M1911','DW715'):
        d=read(R/'Authored'/f'{profile}.json');deform=posed_groups(d);faces=oriented_faces(d)
        axes={}
        for side in ('r','l'):
            for q in anatomy[side]['digits']:
                if q['bone'] not in NAMES:continue
                n=q['bone'];rotation_ref=np.asarray(master['bones'][n]['axes']).T
                rotation_ref/=np.linalg.norm(rotation_ref,axis=0)
                axes[n]=dict(spread=(np.linalg.inv(rotation_ref)@q['dorsal']).tolist(),bend=(np.linalg.inv(rotation_ref)@q['across']).tolist())
        cache={}
        for clip in read(OUT/f'{profile}_motion.json')['clips']:
            samples=clip['samples']
            row=dict(profile=profile,asset=clip['asset'],duration=clip['duration'],axes=axes,keys=[]);previous=np.zeros(11)
            for sample in samples:
                # Remove whole-viewmodel motion from the cache signature.
                hand=np.linalg.inv(matrix(sample['bones']['hand_r']))
                descriptor=np.concatenate([(hand@matrix(sample['bones'][n]))[:3,:].ravel() for n in sample['bones'] if n.startswith(('hand_','pinky_','ring_','middle_'))])
                key=tuple(np.round(descriptor,4))
                prior=next((k for k in previous_output.get(clip['asset'],{}).get('keys',[]) if abs(k['time']-sample['time'])<1e-6),None)
                if key in cache:values,before,after=cache[key]
                elif prior and prior['after']['max_plane_cross_mm']<=.15:
                    values=np.asarray(prior['angles']);before=prior['before'];after=prior['after'];cache[key]=(values,before,after)
                else:
                    case=Case(d,parts,sample,axes,deform,faces);values,before,after=solve(case,np.asarray(prior['angles']) if prior else previous);cache[key]=(values,before,after)
                previous=values
                row['keys'].append(dict(time=sample['time'],angles=values.tolist(),before=before,after=after))
                print('ARMOR_POSE_SOLVE',profile,clip['label'],round(sample['time'],3),'plane_cross_mm',round(before['max_plane_cross_mm'],3),round(after['max_plane_cross_mm'],3),'angles',values.tolist(),flush=True)
            output['clips'].append(row);write(OUT/'pinky-pose-corrections.json',output)
    print('ARMOR_POSE_CURVES_SAVED',len(output['clips']),flush=True)
if __name__=='__main__':main()
