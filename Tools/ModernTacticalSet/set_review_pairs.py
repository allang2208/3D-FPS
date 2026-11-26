"""Local shell/cloth and sleeve/glove interface measurements for TS01."""
import json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'SetFitReview20261115'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json')
def load(key):return read(next(x for x in plan['rows'] if x['key']==key)['candidates'][0])
def tree(p,f):return BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True)
rows=[]
for rig in ['Jason','Kaitlin']:
    d=load(rig+'_shirt_tactical_world');p=np.array(d['positions']);f=np.array(d['triangles']);raw=read(S/'CombatShirtR3/Authored'/f'shirt_cloth_{rig}.json');detail=read(S/'CombatShirtR3/Authored'/f'shirt_detail_{rig}.json');neck=read(S/'CombatShirtR3/Authored'/f'neck_skin_{rig}.json')
    outer=f[(f<len(raw['positions'])//2).all(1)];vest=f[(f>=len(detail['positions'])+len(neck['positions'])).all(1)]
    overlap=tree(p,outer).overlap(tree(p,vest));sf=sorted({a for a,b in overlap});vf=sorted({b for a,b in overlap});centers=p[outer[sf]].mean(1) if sf else np.empty((0,3))
    report=dict(rig=rig,shirt_carrier_intersection=dict(triangle_pairs=len(overlap),shirt_faces=len(sf),carrier_faces=len(vf),bounds=[centers.min(0).tolist(),centers.max(0).tolist()] if len(centers) else None,shirt_face_centers=centers.tolist(),caveat='BVH triangle intersections; seam contacts and layered tangencies require visual interpretation'))
    g=load(rig+'_gloves');gp=np.array(g['positions']);bones={b['name']:np.array(b['position']) for b in d['bones']};report['cuffs']={}
    for side,sign in [('l',1),('r',-1)]:
        w=bones['hand_'+side];axis=w-bones['lowerarm_'+side];axis/=np.linalg.norm(axis)
        q=p[:len(raw['positions'])//2];q=q[q[:,0]*sign>15];dist=-(q-w)@axis;radii=np.linalg.norm(q-w+dist[:,None]*axis,axis=1);sleeve=dist[(radii<7)&(dist<12)&(dist>-.5)]
        q=gp[gp[:,0]*sign>15];gd=-(q-w)@axis;gr=np.linalg.norm(q-w+gd[:,None]*axis,axis=1);glove=gd[(gr<7)&(gd>-5)&(gd<12)]
        report['cuffs'][side]=dict(sleeve_end_from_wrist_cm=float(sleeve.min()),glove_end_from_wrist_cm=float(glove.max()),axial_overlap_cm=float(glove.max()-sleeve.min()))
    pa=load(rig+'_pants_tactical');bo=load(rig+'_boots');pp=np.array(pa['positions']);bp=np.array(bo['positions']);pf=np.array(pa['triangles']);bf=np.array(bo['triangles']);pids=np.unique(pf[[not pa['material_slots'][mi].startswith('NATIVE:') for mi in pa['triangle_materials']]]);bids=np.unique(bf[[not bo['material_slots'][mi].startswith('NATIVE:') for mi in bo['triangle_materials']]])
    report['boot_overlap_cm']={}
    for side,sign in [('l',1),('r',-1)]:
        q=pp[pids];q=q[q[:,0]*sign>0];v=bp[bids];v=v[v[:,0]*sign>0];report['boot_overlap_cm'][side]=float(v[:,2].max()-q[:,2].min())
    rows.append(report);print('PAIR_REVIEW',rig,'vest intersections',len(overlap),'cuffs',report['cuffs'],'boot',report['boot_overlap_cm'],flush=True)
(R/'pair-review.json').write_text(json.dumps(dict(rows=rows,reference_pose_only=True),indent=2),encoding='utf-8')
