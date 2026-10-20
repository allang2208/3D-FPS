"""Triangulate a concave palm perimeter without a fan crossing its boundary."""
import numpy as np
def triangulate(points,normals):
 p=np.array(points);n=np.array(normals);axis=n.mean(0);axis/=np.linalg.norm(axis)
 tangent=p[1]-p[0];tangent-=axis*np.dot(tangent,axis);tangent/=np.linalg.norm(tangent)
 q=np.stack((p@tangent,p@np.cross(axis,tangent)),axis=1)
 def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])
 signed=sum(cross(a,b) for a,b in zip(q,np.roll(q,-1,axis=0)));orient=1 if signed>0 else -1
 def area(a,b,c):return cross(q[b]-q[a],q[c]-q[a])*orient
 def inside(point,a,b,c):
  return min(cross(q[b]-q[a],q[point]-q[a])*orient,cross(q[c]-q[b],q[point]-q[b])*orient,cross(q[a]-q[c],q[point]-q[c])*orient)>=-1e-10
 def valid(tri):
  a,b,c=tri
  return np.dot(np.cross(p[b]-p[a],p[c]-p[a]),n[tri].mean(0))*orient>1e-10
 failed=set()
 def solve(ring):
  if tuple(ring) in failed:return None
  if len(ring)==3:return [ring] if area(*ring)>1e-10 and valid(ring) else None
  ears=[]
  for k,b in enumerate(ring):
   a,c=ring[k-1],ring[(k+1)%len(ring)]
   if area(a,b,c)<=1e-10:continue
   if not valid([a,b,c]):continue
   if any(inside(x,a,b,c) for x in ring if x not in (a,b,c)):continue
   ears.append((np.linalg.norm(p[a]-p[c]),k,[a,b,c]))
  for _,k,tri in sorted(ears):
   rest=solve(ring[:k]+ring[k+1:])
   if rest is not None:return [tri]+rest
  failed.add(tuple(ring));return None
 out=solve(list(range(len(p))))
 if out is None:raise RuntimeError('No fold-free triangulation of native palm boundary')
 return out
