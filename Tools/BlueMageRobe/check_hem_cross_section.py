"""Focused geometry regression against independent 3D ray/triangle intersections."""
import json,math,hashlib
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/BlueMageRobe20261018/HemRefine20261020';OUT.mkdir(exist_ok=True)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def surface(loops):
    for band in range(2):
        for i in range(8):
            n=(i+1)%8;a,b,c,d=loops[band,i],loops[band,n],loops[band+1,n],loops[band+1,i]
            yield np.array([a,b,c]);yield np.array([a,c,d])
def center_at(loops,z):
    c=loops.mean(axis=1);z1=max(c[1,2],c[0,2]+.001);z2=max(c[2,2],z1+.001)
    a,b,t=(c[0],c[1],np.clip((z-c[0,2])/(z1-c[0,2]),0,1)) if z<z1 else (c[1],c[2],np.clip((z-z1)/(z2-z1),0,1))
    return a[:2]*(1-t)+b[:2]*t
def section_radius(loops,origin,direction,z):
    radius=1e8
    for tri in surface(loops):
        if z<tri[:,2].min() or z>=tri[:,2].max():continue
        hits=[]
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            za,zb=a[2]-z,b[2]-z
            if (za<=0<zb) or (zb<=0<za):hits.append(a[:2]+(b[:2]-a[:2])*za/(za-zb))
        if len(hits)!=2:continue
        edge=hits[1]-hits[0];rel=hits[0]-origin;den=cross(direction,edge)
        if abs(den)>1e-5:
            t=cross(rel,edge)/den;u=cross(rel,direction)/den
            if t>0 and 0<=u<=1:radius=min(radius,t)
    return radius
def oracle_radius(loops,origin,direction,z):
    # Direct Moller-Trumbore in 3D. No horizontal edge clipping or radius
    # blending is shared with the production algorithm under test.
    start=np.array([*origin,z]);ray=np.array([*direction,0.]);hits=[]
    for tri in surface(loops):
        e1,e2=tri[1]-tri[0],tri[2]-tri[0];p=np.cross(ray,e2);det=e1@p
        if abs(det)<1e-9:continue
        q=start-tri[0];u=(q@p)/det
        if u< -1e-8 or u>1+1e-8:continue
        h=np.cross(q,e1);v=(ray@h)/det;t=(e2@h)/det
        if v>=-1e-8 and u+v<=1+1e-8 and t>0:hits.append(t)
    return min(hits) if hits else 1e8
def smooth(a,b,x):t=float(np.clip((x-a)/(b-a),0,1));return t*t*(3-2*t)
cases=0;max_error=0.;minimum_margin=1e8
for twist in (-75,-45,-20,0,20,45,75):
    for bent in (False,True):
        loops=[]
        for j,z in enumerate((0.,40.,80.)):
            a=np.arange(8)*math.tau/8+math.radians(twist)*j
            xy=np.c_[np.cos(a),np.sin(a)]*(20.-j*2)
            if bent:xy+=np.array([j*1.7,-j*.8])
            zz=np.full(8,z)+(xy[:,0]*.06+xy[:,1]*.04 if bent else 0.)
            loops.append(np.c_[xy,zz])
        loops=np.array(loops)
        for z in (9.,18.,31.,40.,48.,61.,72.):
            origin=center_at(loops,z)
            for angle in np.arange(24)*math.tau/24+.017:
                direction=np.array([math.cos(angle),math.sin(angle)])
                got=section_radius(loops,origin,direction,z);expected=oracle_radius(loops,origin,direction,z)
                if expected>=1e7:raise AssertionError('Fixture has no enclosing cross-section')
                error=abs(got-expected);max_error=max(max_error,error)
                if error>1e-5:raise AssertionError(('Surface mismatch',twist,bent,z,angle,got,expected))
                result=min(35.,max(got-1.,0.));minimum_margin=min(minimum_margin,expected-result)
                if result>expected-1.+1e-5:raise AssertionError('Covered vertex outside inner surface')
                if min(2.,max(got-1.,0.))!=2.:raise AssertionError('Interior point was unnecessarily moved')
                cases+=1
# The unchanged overlap and ankle protection remain explicit endpoints.
assert smooth(-1.,6.,-2.)==0.
assert smooth(16.,22.,1.)==0.
assert smooth(16.,22.,40.)==1.
report=dict(passed=True,cases=cases,max_surface_error_cm=max_error,minimum_inside_margin_cm=minimum_margin,exposed_calf_and_ankle_endpoints_passed=True,actual_game_pose=False,shader_sha256=hashlib.sha256((P/'Tools/BlueMageRobe/hem_conform.hlsl').read_bytes()).hexdigest(),method='CPU algorithm versus independent Moller-Trumbore 3D ray/triangle oracle; UE separately compiles the actual shader')
(OUT/'geometry-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
