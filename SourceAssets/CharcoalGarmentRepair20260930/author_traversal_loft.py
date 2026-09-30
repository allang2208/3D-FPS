"""Rebuild clean short sleeves around native upper-arm cross sections."""
import sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from author import read,write,bary,weights,recalc
def build():
 d=read(R/'Authored/Traversal.json');skin=read(R/'Before/Traversal/skin.json');sp=np.array(skin['positions']);sf=np.array(skin['triangles']);sm=np.array(skin['materials'])
 d.update(positions=[],weights=[],triangles=[],uv=[],normals=[],triangle_materials=[])
 N=80;rows=24;tau=math.tau
 for side in ['l','r']:
  a=np.array(d['bones']['upperarm_'+side]['position']);b=np.array(d['bones']['lowerarm_'+side]['position']);axis=(b-a)/np.linalg.norm(b-a);sign=np.sign(a[0]);length=np.linalg.norm(b-a)*.55
  x=np.array([0.,1.,0.]);x-=axis*np.dot(x,axis);x/=np.linalg.norm(x);y=np.cross(axis,x)
  faces=sf[(sm==0)&np.all(sp[sf,0]*sign>0,axis=1)];tree=BVHTree.FromPolygons([Vector(p) for p in sp],faces.tolist(),all_triangles=True)
  stations=np.linspace(-1.,length,rows);radii=np.zeros((rows,N));ws={}
  for j,t in enumerate(stations):
   center=a+axis*t
   for i in range(N):
    direction=x*math.cos(tau*i/N)+y*math.sin(tau*i/N);origin=center.copy();travel=0.;hits=[]
    for _ in range(6):
     hit,normal,fi,dist=tree.ray_cast(Vector(origin),Vector(direction),16-travel)
     if hit is None:break
     travel=float((np.array(hit)-center)@direction)
     tri=sp[faces[fi]];outward=-np.cross(tri[1]-tri[0],tri[2]-tri[0])
     if outward@direction>0:hits.append((travel,hit,fi))
     origin=np.array(hit)+direction*.002;travel+=.002
    if hits:
     radius,hit,fi=max(hits,key=lambda z:z[0]);radii[j,i]=radius;ws[j,i]=weights(skin,faces[fi],bary(hit,sp[faces[fi]]))
  # The root of a first-person bare arm is intentionally open. Use the closest
  # complete native cross section for any missing ray, never a torso-wide cap.
  for j in range(rows):
   for i in range(N):
    if radii[j,i]>0:continue
    choices=[k for k in range(rows) if radii[k,i]>0]
    if not choices:raise RuntimeError('Missing native upper-arm section')
    k=min(choices,key=lambda k:abs(k-j));radii[j,i]=radii[k,i];ws[j,i]=ws[k,i]
  smooth=(np.roll(radii,1,1)+2*radii+np.roll(radii,-1,1))/4
  radii=np.maximum(radii,smooth)
  offset=len(d['positions'])
  for layer,clearance in enumerate([.85,.60]):
   for j,t in enumerate(stations):
    for i in range(N):
     direction=x*math.cos(tau*i/N)+y*math.sin(tau*i/N)
     shoulder_ease=.95*max(0.,1.-max(0.,t)/6.)**2
     d['positions'].append((a+axis*t+direction*(radii[j,i]+clearance+shoulder_ease)).tolist());d['weights'].append(ws[j,i])
  def vi(layer,j,i):return offset+layer*rows*N+j*N+i%N
  def face(ids,coords,mat,outward):
   p=np.array([d['positions'][i] for i in ids]);cross=np.cross(p[1]-p[0],p[2]-p[0])
   if cross@outward>0:ids=ids[::-1];coords=coords[::-1]
   d['triangles'].append(ids);d['uv'].append(coords);d['triangle_materials'].append(mat)
  for layer in [0,1]:
   for j in range(rows-1):
    for i in range(N):
     ids=[vi(layer,j,i),vi(layer,j,i+1),vi(layer,j+1,i+1),vi(layer,j+1,i)];u0=tau*6*i/N/25;u1=tau*6*(i+1)/N/25;coords=[[u0,stations[j]/25],[u1,stations[j]/25],[u1,stations[j+1]/25],[u0,stations[j+1]/25]]
     outward=(x*math.cos(tau*(i+.5)/N)+y*math.sin(tau*(i+.5)/N))*(1 if layer==0 else -1)
     for ids2 in [[0,1,2],[0,2,3]]:face([ids[k] for k in ids2],[coords[k] for k in ids2],0 if layer==0 else 2,outward)
  for j in [0,rows-1]:
   for i in range(N):
    ids=[vi(0,j,i),vi(0,j,i+1),vi(1,j,i+1),vi(1,j,i)];coords=[[i/N,0],[(i+1)/N,0],[(i+1)/N,.25/25],[i/N,.25/25]]
    for ids2 in [[0,1,2],[0,2,3]]:face([ids[k] for k in ids2],[coords[k] for k in ids2],1,axis*(-1 if j==0 else 1))
 recalc(d);d['contract']='Charcoal native V7 Traversal short sleeves rebuilt from 24 native upper-arm cross sections; matched inner/outer weights; explicit open thickness rings; no shoulder cap; cotton material preserved'
 write(R/'Authored/Traversal.json',d);print('CHARCOAL_TRAVERSAL_LOFT',len(d['positions']),len(d['triangles']),flush=True)
if __name__=='__main__':build()
