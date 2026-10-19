"""The approved robe cuffs on every current native first-person binding."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bmesh,numpy as np
from mathutils import Vector
from geometry import *
from paired_surface import relax
from native_sweep import surface

def build(row):
    skin=read(row['file']);profile=row['profile'];bones=skin['bones'];names=sorted(bones);d=new_mesh(profile,skin)
    side=[max(('l','r'),key=lambda s:sum(v for n,v in w.items() if n.endswith('_'+s))) for w in skin['weights']]
    report={}
    for suffix in ('l','r'):
        fs=[f for f in skin['triangles'] if all(side[i]==suffix for i in f)]
        if not fs:continue
        a,e,w=[np.array(bones[n+'_'+suffix]['position']) for n in ('upperarm','lowerarm','hand')];upper=unit(e-a);lower=unit(w-e);radial=None
        if profile in ('ASH12','M16','Super90'):
            p,f,ws,edges,radial=surface(skin,suffix,1.,segments=80,rows=64)
        else:
            bm=bmesh.new();dw=bm.verts.layers.deform.verify();used=sorted({i for face_ids in fs for i in face_ids});verts={i:bm.verts.new(skin['positions'][i]) for i in used}
            for i,v in verts.items():
                for name,value in skin['weights'][i].items():v[dw][names.index(name)]=value
            for ids in fs:bm.faces.new([verts[i] for i in ids])
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
            for point,axis,inside,outside in [(a+upper,upper,True,False),(w-lower,lower,False,True),(w-lower*4.5,lower,False,False)]:
                bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector(point),plane_no=Vector(axis),dist=.00001,clear_inner=inside,clear_outer=outside)
            bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
            p=np.array([v.co[:] for v in bm.verts]);f=np.array([[v.index for v in face_ids.verts] for face_ids in bm.faces]);ws=[norm_weights({names[k]:v for k,v in pt[dw].items()}) for pt in bm.verts];edges=boundary(f);bm.free()
        prox=-(p-w)@lower;cuff=1-smooth((prox-4.5)/3.5);clearance=.32+.30*(1-cuff)
        p,n,construction=relax(p,f,edges,clearance,a+upper,upper,thickness=.14,directions=radial)
        seed=unit(np.cross(upper,lower))
        if np.linalg.norm(seed)<.5:seed=unit(np.cross(upper,[0,1,0]))
        blend=smooth(((p-e)@lower+4)/8);axis=(1-blend[:,None])*upper+blend[:,None]*lower;axis/=np.linalg.norm(axis,axis=1)[:,None]
        q=p-e;theta=np.arctan2(np.einsum('ij,ij->i',q,np.cross(axis,seed)),q@seed)/math.tau;along=np.linalg.norm(e-a)+np.einsum('ij,ij->i',q,axis)
        def tex(ids,_):
            coords=np.column_stack((theta[ids],along[ids]/25));coords[:,0][coords[:,0]<0]+=1
            if np.ptp(coords[:,0])>.5:coords[:,0][coords[:,0]<.5]+=1
            if np.mean(prox[ids])<4.5:coords[:,1]=(prox[ids]-1)/3.5
            else:coords[:,0]*=1.2
            return coords
        paired(d,p,f,ws,clearance,.14,lambda fi,ids:2 if np.mean(prox[ids])<4.5 else 1,tex,lambda fi,ids:3,n)
        report[suffix]=dict(cuff_from_wrist_cm=1,cuff_band_cm=3.5,inner_clearance_cm=.18,paired_weights=True,construction=construction)
    finish(d);write(R/'Authored/FP'/(profile+'.json'),d)
    print('BLUE_ROBE_FP_AUTHORED',profile,len(d['triangles']),flush=True);return report

if __name__=='__main__':
    reports={}
    for row in read(R/'input_inventory.json')['rows']:
        if row['profile'] in ('Body','Jason'):continue
        reports[row['profile']]=build(row);write(R/'sleeve_authoring.json',reports)
