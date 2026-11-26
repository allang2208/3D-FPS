"""Ease the confirmed local Body sleeve contact while keeping cuff length."""
import sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write,unit,normals
from shirt_geometry import subset
from combat2_details import sew
file=C/'Authored/shirt_fp_Body.json';d=read(file)
if d['cloth_production'].get('local_wrist_clearance_method')!='native_overlap_face_ease_v2':
    base_count=max(part['first_vertex']+part['vertices'] for part in d['parts']);d=subset(d,(np.array(d['triangles'])<base_count).all(1));d['materials']=d['materials'][:3];d['material_slots']=d['material_slots'][:3];p=np.array(d['positions']);f=np.array(d['triangles']);new=p.copy();g=read(C/'Authored/gloves_Body.json');tree=BVHTree.FromPolygons(g['positions'],g['triangles'],all_triangles=True);bones={b['name']:np.array(b['position']) for b in d['bones']};records={}
    for part in d['parts']:
        side=part['name'][-1];start=part['first_vertex'];count=part['vertices']//2;ids=np.arange(start,start+count);q=p[ids];w=bones['hand_'+side];axis=unit(w-bones['lowerarm_'+side]);dist=-(q-w)@axis;radial=q-(w-dist[:,None]*axis);radius=np.linalg.norm(radial,axis=1);direction=radial/radius[:,None];required=np.zeros(count)
        for i in np.flatnonzero((dist>1.5)&(dist<6.)):
            center=w-axis*dist[i];hit=tree.ray_cast(Vector(center+direction[i]*12),Vector(-direction[i]),12.)
            if hit[0] is not None:required[i]=max(0.,np.linalg.norm(np.array(hit[0])-center)+.24-radius[i])
        tri=f[((f>=start)&(f<start+count)).all(1)]-start;sleeve=BVHTree.FromPolygons(q.tolist(),tri.tolist(),all_triangles=True);gnames={b['index']:b['name'] for b in g['bones']};face_contacts=0
        for gp,weights in zip(np.array(g['positions']),g['weights']):
            if sum(value for bi,value in weights if gnames[bi].endswith('_'+side))<.5:continue
            along=-np.dot(gp-w,axis)
            if not dist.min()+.25<along<6.:continue
            center=w-axis*along;dr=unit(gp-center);hit=sleeve.ray_cast(Vector(center),Vector(dr),12.)
            if hit[0] is None:continue
            needed=np.linalg.norm(gp-center)+.24-np.linalg.norm(np.array(hit[0])-center)
            if needed<=0:continue
            face_contacts+=1
            for vi in tri[hit[2]]:required[vi]=max(required[vi],needed/max(.5,float(np.dot(direction[vi],dr))))
        edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),1);edges=np.unique(edges,axis=0);delta=required.copy();degree=np.zeros(count)
        np.add.at(degree,edges[:,0],1);np.add.at(degree,edges[:,1],1)
        for _ in range(24):
            acc=delta*4;np.add.at(acc,edges[:,0],delta[edges[:,1]]);np.add.at(acc,edges[:,1],delta[edges[:,0]]);delta=np.maximum(required,acc/(degree+4))
        moved=q+direction*delta[:,None];new[ids]=moved;new[ids+count]=moved-normals(moved,tri)*.12;records[side]=dict(max_outward_ease_cm=float(delta.max()),directly_contacting_vertices=int(np.count_nonzero(required)),contact_samples=face_contacts,cuff_axial_position_unchanged=True)
    d['positions']=new.tolist();d['normals']=normals(new,f)[f].tolist();sew(d);d['materials']=[m.replace('CombatShirtR2','CombatShirtR3') for m in d['materials']];d['cloth_production']['local_wrist_clearance']=records;d['cloth_production']['local_wrist_clearance_method']='native_overlap_face_ease_v2';write(file,d);write(C/'Review/Body-local-wrist-ease.json',records);print('BODY_LOCAL_WRIST_CLEARANCE',records,flush=True)
