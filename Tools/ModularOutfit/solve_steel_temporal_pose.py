"""Preserve valid armor clearance through a clip instead of resetting each frame.

Consumes existing native samples. Produces a candidate curve source; promotion
and native compilation are separate production steps. Does not launch UE.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_leather_gloves import read,write
from solve_steel_finger_pose import R,OUT,NAMES,Case,oriented_faces
from steel_motion_contacts import posed_groups

LIMITS=np.array([8.,8.,10.,10.]*2+[.3]*3)
SCALE=np.array([1.]*8+[.02]*3)

def bounded(value):
    value=np.clip(value,-LIMITS,LIMITS)
    length=np.linalg.norm(value[8:])
    if length>.3:value[8:]*=.3/length
    return value

def solve(case,previous,candidates):
    # Continuity is part of the solve, not an averaging pass after it.
    case.objective(previous);initial=dict(case.last)
    case.objective(np.zeros(11));before=dict(case.last)
    if initial['crossing_pairs']==0:return previous.copy(),before,initial
    def score(value):
        cost=case.objective(value)
        return cost+float(np.square((value-previous)/SCALE).sum())*.0003
    best=previous.copy();best_score=score(best)
    for value in [np.zeros(11),*candidates]:
        value=bounded(np.asarray(value,float).copy());cost=score(value)
        if cost<best_score:best=value;best_score=cost
    for step in (4.,2.,1.,.5):
        for sweep in range(3):
            changed=False
            for axis in range(11):
                for sign in (-1,1):
                    value=best.copy();value[axis]+=step*sign*SCALE[axis];value=bounded(value)
                    cost=score(value)
                    if cost<best_score:best=value;best_score=cost;changed=True
            if not changed:break
    case.objective(best)
    # Bounded stochastic refinement escapes plate-edge local minima without
    # demanding a large hand move or sacrificing dorsal armor coverage.
    if case.last['max_plane_cross_mm']>.04:
        rng=np.random.default_rng(220928)
        mean=best.copy();sigma=SCALE*2.5
        for generation in range(8):
            population=[best.copy()]+[bounded(mean+rng.normal(size=11)*sigma) for _ in range(23)]
            results=sorted([(score(value),i) for i,value in enumerate(population)])
            if results[0][0]<best_score:best_score=results[0][0];best=population[results[0][1]].copy()
            elite=np.array([population[index] for _,index in results[:6]])
            mean=elite.mean(0);sigma=np.maximum(elite.std(0),SCALE*.18)
            case.objective(best)
            if case.last['crossing_pairs']==0:break
    case.objective(best)
    return best,before,dict(case.last)

def main():
    source=read(OUT/'pinky-pose-corrections.json');runtime=read(OUT/'runtime-pose-curves.json')
    runtime={c['asset']:c for c in runtime['clips']}
    parts=read(R/'parts.json');output=dict(source,clips=[],temporal_clearance=True)
    for profile in ('M4','M1911','DW715'):
        d=read(R/'Authored'/f'{profile}.json');deform=posed_groups(d);faces=oriented_faces(d)
        motions={c['asset']:c for c in read(OUT/f'{profile}_motion.json')['clips']}
        authored=[c for c in source['clips'] if c['profile']==profile]
        idle=np.array(authored[0]['keys'][0]['angles'])
        for clip in authored:
            if profile=='M4' and 'reload_empty' not in clip['asset']:
                output['clips'].append(clip);continue
            motion=motions[clip['asset']];samples=motion['samples'];row=dict(clip,keys=[],temporal_clearance=True)
            previous=idle.copy()
            for index,sample in enumerate(samples):
                # Stable aim uses t=0 in the runtime graph.
                if motion['label'] in ('idle','aim') and index>0:
                    row['keys'].append(dict(row['keys'][0],time=sample['time']));continue
                case=Case(d,parts,sample,clip['axes'],deform,faces)
                candidates=[idle]+[k['angles'] for k in clip['keys'][max(0,index-2):index+3]]
                key=runtime[clip['asset']]['keys'][index]
                candidates.append(key['angles']+key.get('left_hand_offset_cm',[0.,0.,0.]))
                values,before,after=solve(case,previous,candidates);previous=values
                row['keys'].append(dict(time=sample['time'],angles=values.tolist(),before=before,after=after))
                print('STEEL_TEMPORAL_SOLVE',profile,motion['label'],round(sample['time'],3),
                    'cross_mm',round(after['max_plane_cross_mm'],4),'pairs',after['crossing_pairs'],flush=True)
            output['clips'].append(row);write(OUT/'pinky-pose-temporal.json',output)
            if motion['label']=='idle':idle=np.array(row['keys'][0]['angles'])
    print('STEEL_TEMPORAL_COMPLETE',len(output['clips']),flush=True)

if __name__=='__main__':main()
