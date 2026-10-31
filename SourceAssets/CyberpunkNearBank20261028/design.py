"""Near-bank-only authored generation. Coordinates are final UE world metres."""
from pathlib import Path
import math,bisect
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
BASE='/Game/Props/CyberpunkNearBank20261028'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OWNER='CyberpunkApartment.NearBank20261028'
GROUND=-108.75
WATER=-112.5
SEED=281026
HOST=(-17.81,-42.81,47.81,17.74)
# Source near-bank outline only; do not apply the opposite-bank -768.75 m offset.
KNOTS=sorted([((-x+10)*1.25,y*1.25) for x,y in [(-2200,-180),(-1100,-80),(-400,28),(0,36),(500,72),(1400,10),(2500,-240)]])
X=[p[0] for p in KNOTS];Y=[p[1] for p in KNOTS]
D=[(Y[i+1]-Y[i])/(X[i+1]-X[i]) for i in range(len(X)-1)]
M=[D[0]]
for i in range(1,len(X)-1):
    a,b=D[i-1],D[i];h0=X[i]-X[i-1];h1=X[i+1]-X[i]
    M.append(0 if a*b<=0 else (3*(h0+h1))/((2*h1+h0)/a+(h1+2*h0)/b))
M.append(D[-1])
NODES=[-440,-260,-80,110,300,500]
def legacy_y(x):
    i=max(0,min(len(X)-2,bisect.bisect_right(X,x)-1));t=(x-X[i])/(X[i+1]-X[i]);return Y[i]*(1-t)+Y[i+1]*t
def shore_y(x):
    i=max(0,min(len(X)-2,bisect.bisect_right(X,x)-1));h=X[i+1]-X[i];t=(x-X[i])/h
    y=(2*t**3-3*t*t+1)*Y[i]+(t**3-2*t*t+t)*h*M[i]+(-2*t**3+3*t*t)*Y[i+1]+(t**3-t*t)*h*M[i+1]
    fade=math.sin(math.pi*(x-X[0])/(X[-1]-X[0]))**2
    return y+fade*(1.25*math.sin(x/117)+.65*math.sin(x/53+.6))
def frame(x,offset=0,z=GROUND):
    slope=(shore_y(min(X[-1],x+.05))-shore_y(max(X[0],x-.05)))/max(.00001,min(X[-1],x+.05)-max(X[0],x-.05))
    length=math.hypot(1,slope);return [x+offset*slope/length,shore_y(x)-offset/length,z]
def tangent(x):
    a=frame(x-.1);b=frame(x+.1);return math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
def walk_width(x):return 8+sum(4.2*math.exp(-((x-a)/20)**2) for a in NODES)
BUILDINGS=[
 dict(id='N1_01',style='NYH_Ref_N1',p=[-140,-92,GROUND],yaw=0),
 dict(id='N1_02',style='NYH_Ref_N1',p=[-62,-92,GROUND],yaw=0),
 dict(id='N1_03',style='NYH_Ref_N1',p=[92,-92,GROUND],yaw=0),
 dict(id='N1_04',style='NYH_Ref_N1',p=[167,-92,GROUND],yaw=0),
 dict(id='N1_05',style='CHI_Ref_A1_N1',p=[-95,-218,GROUND],yaw=0),
 dict(id='N1_06',style='CHI_Ref_A1_N1',p=[95,-218,GROUND],yaw=0)]
ROADS=[dict(a=[-215,-160],b=[235,-160],width=16),dict(a=[-215,-160],b=frame(-215,36)[:2],width=12),dict(a=[235,-160],b=frame(235,36)[:2],width=12)]
