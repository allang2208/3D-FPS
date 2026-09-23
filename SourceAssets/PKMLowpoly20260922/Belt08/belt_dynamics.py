"""Offline, fixed-step secondary motion for the visual cartridge belt."""
from mathutils import Vector
import math

def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)

def project(points,lengths,tip,inlet,iterations=40):
 """Two pinned ends, rigid inter-cartridge distances (no scale animation)."""
 for _ in range(iterations):
  points[0]=tip.copy()
  for i,d in enumerate(lengths):
   v=points[i+1]-points[i]
   if v.length>1e-9:points[i+1]=points[i]+v.normalized()*d
  points[-1]=inlet.copy()
  for i in range(len(lengths)-1,-1,-1):
   v=points[i]-points[i+1]
   if v.length>1e-9:points[i]=points[i+1]+v.normalized()*lengths[i]
 points[0]=tip.copy();points[-1]=inlet.copy()
 return points

class BeltDynamics:
 def __init__(self,lengths):
  self.lengths=lengths;self.p=None
 def step(self,guide,W,activation):
  target=[W@p for p in guide];dt=1/240
  if self.p is None or activation<=0:
   self.p=[p.copy() for p in target];self.prev=[p.copy() for p in target];self.guide=target
   return [p.copy() for p in guide]
  for sub in range(4):
   goals=[a.lerp(b,(sub+1)/4) for a,b in zip(self.guide,target)]
   for i in range(1,len(target)-1):
    old=self.p[i].copy();velocity=(old-self.prev[i])*math.exp(-13*dt)
    self.p[i]+=velocity+(Vector((0,0,-9.81))+(goals[i]-old)*1050)*dt*dt
    # A small guide corridor represents the clearance around the feed shelf
    # and box mouth; large box motions cannot throw the chain through them.
    offset=self.p[i]-goals[i]
    if offset.length>.004:self.p[i]=goals[i]+offset.normalized()*.004
    self.prev[i]=old
   project(self.p,self.lengths,goals[0],goals[-1],12)
  self.guide=target
  # Reproject AFTER settling blend; blending alone changes segment lengths.
  out=[g.lerp(p,activation) for g,p in zip(target,self.p)]
  project(out,self.lengths,target[0],target[-1],60)
  inv=W.inverted();return [inv@p for p in out]
