"""Deterministic 240 Hz constrained belt dynamics, baked into the reload clips.

World-space inertia/gravity; inlet and handled tip are pinned, intermediate
links retain their measured lengths. This is offline simulation, not UE physics.
"""
from mathutils import Vector
import math

class BeltDynamics:
 def __init__(self,centers):
  self.centers=centers
  self.lengths=[(centers[i+1]-centers[i]).length for i in range(5)]
  self.p=None
 def step(self,t,guide,W,box):
  target=[W@p for p in guide[:6]]
  if self.p is None or t==0:
   self.p=[p.copy() for p in target];self.prev=[p.copy() for p in target];self.guide=target
  inv=W.inverted();dt=1/240
  for sub in range(4):
   goals=[a.lerp(b,(sub+1)/4) for a,b in zip(self.guide,target)]
   for i in range(1,5):
    p=self.p[i].copy();velocity=(p-self.prev[i])*math.exp(-9*dt)
    # Flexural memory of the metal links prevents a rope-like collapse.
    self.p[i]+=velocity+(Vector((0,0,-9.81))+(goals[i]-p)*850)*dt*dt
    self.prev[i]=p
   for _ in range(18):
    self.p[0]=goals[0].copy();self.p[5]=goals[5].copy()
    for i,length in enumerate(self.lengths):
     delta=self.p[i+1]-self.p[i];n=delta.length
     if n<1e-8:continue
     a=0 if i==0 else 1;b=0 if i+1==5 else 1
     correction=delta*(n-length)/(n*(a+b))
     self.p[i]+=correction*a;self.p[i+1]-=correction*b
    for i in range(1,5):
     local=inv@self.p[i]
     # Receiver feed shelf collision. Box interior links remain rigidly stored.
     if -.043<local.x<.029 and -.005<local.y<.084:
      local.z=max(local.z,.067)
     b=box.inverted()@local
     if -.106<b.x<.106 and -.010<b.y<.089:b.z=max(b.z,-.025)
     self.p[i]=W@(box@b)
   self.p[0]=goals[0].copy();self.p[5]=goals[5].copy()
  self.guide=target
  # The feed pawl seats the chain before closing: exact authored loop endpoints.
  activation=min(1,t/.4)*max(0,min(1,(5.65-t)/.35))
  result=[p.copy() for p in guide]
  for i in range(1,5):result[i]=guide[i].lerp(inv@self.p[i],activation)
  return result
