"""Dedicated modern boot fit: cloth outside calf above cuff, tucked inside below."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import *
R=S/'CombatShirtR2'
from mathutils import Vector
from mathutils.bvhtree import BVHTree
for rig,cuff in [('Jason',28.5),('Kaitlin',27.85)]:
    d=read(R/'Authored'/f'pants_{rig}.json');boot=read(S/'Integration/Delivery'/f'boots_{rig}_Wear.json')
    bp=np.array(boot['positions']);bf=np.array(boot['triangles']);skin=np.array([boot['material_slots'][i].startswith('NATIVE:') for i in boot['triangle_materials']])
    bones={b['name']:np.array(b['position']) for b in boot['bones']};original=np.array(d['positions']);p=original.copy();faces=np.array(d['triangles'])
    cloth=np.unique(faces[[not d['material_slots'][i].startswith('NATIVE:') for i in d['triangle_materials']]])
    def center(z,side):
        a,b=bones['foot_'+side],bones['calf_'+side];return a+(b-a)*((z-a[2])/(b[2]-a[2]))
    def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
    body=read(R/'Inputs'/f'Body_{rig}.json');bodyp=np.array(body['positions']);bodyf=np.array(body['triangles'])
    for side,sign in [('l',1),('r',-1)]:
        sm=skin & (bp[bf].mean(1)[:,0]*sign>0);tree=BVHTree.FromPolygons(bp.tolist(),bf[sm].tolist(),all_triangles=True)
        bodymask=(bodyp[bodyf].mean(1)[:,0]*sign>0)&(bodyp[bodyf].mean(1)[:,2]<58)&(bodyp[bodyf].mean(1)[:,2]>12)
        bodytree=BVHTree.FromPolygons(bodyp.tolist(),bodyf[bodymask].tolist(),all_triangles=True)
        base_mask=(np.array(d['triangle_materials'])==d['material_slots'].index('TS01_RangerRipstop'))&(original[faces].mean(1)[:,0]*sign>0)
        panttree=BVHTree.FromPolygons(original.tolist(),faces[base_mask].tolist(),all_triangles=True)
        # Continuous cylindrical field sampled from BOTH the native leg and the
        # boot's skin insert. Every sewn layer receives the same displacement.
        zs=np.linspace(20,50,61);angles=np.arange(128)*2*np.pi/128;field=np.zeros((61,128))
        for iz,z in enumerate(zs):
            c=center(z,side)
            for it,theta in enumerate(angles):
                direction=np.array([np.cos(theta),np.sin(theta),0.]);hits=[]
                for surface in [tree,bodytree,panttree]:
                    hit=surface.ray_cast(Vector(c+direction*15),Vector(-direction),15)[0]
                    hits.append(None if hit is None else float(np.dot(np.array(hit)-c,direction)))
                skinr=max(v for v in hits[:2] if v is not None) if any(v is not None for v in hits[:2]) else None
                base=hits[2]
                if skinr is None or base is None:field[iz,it]=np.nan;continue
                outside=max(0,skinr+.85-base);inside=min(0,skinr+.1-base)
                field[iz,it]=(inside+(outside-inside)*smooth((z-(cuff-2.8))/2.2))*(1-smooth((z-44)/6))
        for iz in range(len(zs)):
            valid=np.isfinite(field[iz]);inds=np.flatnonzero(valid)
            if len(inds)<3:raise RuntimeError('Insufficient native calf envelope')
            field[iz]=np.interp(np.arange(128),np.r_[inds-128,inds,inds+128],np.tile(field[iz,valid],3))
        for _ in range(3):field=(field*4+np.roll(field,1,1)+np.roll(field,-1,1)+np.vstack([field[:1],field[:-1]])+np.vstack([field[1:],field[-1:]]))/8
        for i in cloth:
            q=p[i]
            if q[0]*sign<=0 or q[2]>50 or q[2]<20:continue
            c=center(q[2],side);v=q-c;v[2]=0;r=np.linalg.norm(v);direction=unit(v)
            zf=(q[2]-20)*2;iz=min(59,int(zf));fz=zf-iz;tf=(np.arctan2(v[1],v[0])%(2*np.pi))*128/(2*np.pi);it=int(tf)%128;ft=tf-int(tf)
            delta=(field[iz,it]*(1-ft)+field[iz,(it+1)%128]*ft)*(1-fz)+(field[iz+1,it]*(1-ft)+field[iz+1,(it+1)%128]*ft)*fz
            radius=r+delta
            p[i]=c+direction*radius;p[i,2]=q[2]
    d['positions']=p.tolist();smooth_transport(d,original)
    d['materials']=[s[7:] if s.startswith('NATIVE:') else '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+s.removeprefix('TS01_') for s in d['material_slots']]
    d['contract']='Dedicated TS01 calf envelope, continuous all-layer warp, native waist unchanged; cuff overlap below actual modern boot top'
    write(R/'Authored'/f'pants_tactical_{rig}.json',d);print('TS01_PANTS_AUTHORED',rig,len(d['triangles']),flush=True)
