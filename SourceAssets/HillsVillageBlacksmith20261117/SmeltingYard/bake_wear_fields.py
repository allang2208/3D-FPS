"""Bake non-tiling metric dirt masks. The scanned canvas, grain, metal and soil still supply the PBR detail."""
from pathlib import Path
import sys
import math
import random
import numpy as np
from PIL import Image
from yard_sites import BAY_Y, bay, wall, WEST, HALF
source=Path(__file__).resolve().parent
sys.path.insert(0,str(source.parents[2]/'Tools/WorldGeneration/AbandonedVillage'))
from smith_apron import cart_wheelways
from village_tread import ramp, tread

out=source/'Wear'
out.mkdir(exist_ok=True)
def axes(width,height):
    return ((np.arange(width,dtype='f')+.5)/width)[None,:],((np.arange(height,dtype='f')+.5)/height)[:,None]
def noise(width,height,cx,cy,seed):
    rng=np.random.default_rng(seed)
    lattice=Image.fromarray(rng.integers(0,256,(cy+2,cx+2),dtype=np.uint8))
    return (np.asarray(lattice.resize((width,height),Image.Resampling.BICUBIC),dtype='f')/127.5-1.)
def save(name,*channels):
    Image.fromarray(np.uint8(255*np.clip(np.stack(np.broadcast_arrays(*channels),axis=-1),0,1)+.5)).save(out/(name+'.png'))
def field(x,y,cx,cy,rx,ry):
    return np.exp(-((x-cx)/rx)**2-((y-cy)/ry)**2)

def roof():
    w,h=2048,1024
    u,v=axes(w,h)
    y=(v-.5)*(2*HALF)
    x=WEST+u*(wall(y)+.12-WEST)
    clouds=noise(w,h,42,32,155)*.57+noise(w,h,122,92,17)*.27+noise(w,h,460,318,633)*.16
    soot=np.zeros((h,w),'f')
    for j,by in enumerate(BAY_Y):
        bx,_=bay(by)
        plume=field(x,y,bx+.04,by,1.12,.77+.08*j)
        drift=field(x,y,bx-1.06,by+.18,1.90,.89)
        soot=np.maximum(soot,(.77*plume+.38*drift)*(.91+.40*clouds))
    runoff=noise(w,h,7,230,45)*.50+.5
    tide=np.exp(-((x-WEST-.19-.060*clouds)/.19)**2)
    damp=np.clip(.47*tide+.44*runoff**1.8*(.28+.72*(1-u)**1.6)+.19*clouds,0,1)
    seam=np.maximum.reduce([np.broadcast_to(np.exp(-((y-c)/.045)**2),(h,w)) for c in (-2.60,-.87,.87,2.60)])
    bleach=np.clip(.34+.20*clouds+.23*seam+.13*(1-u),0,1)
    save('Roof',soot,damp,bleach)

def wall_bloom():
    w,h=1024,1024
    u,v=axes(w,h)
    # At -2 degrees yaw the socket Y axis follows the wall; texture U runs from bottom to top.
    z=2.54+(u-.5)*3.52
    y=.30+(v-.5)*4.52
    cloud=noise(w,h,34,23,41)*.50+noise(w,h,87,49,34)*.30+noise(w,h,390,370,302)*.20
    streak=(noise(w,h,14,220,12)*.5+.5)**2
    black=np.zeros((h,w),'f')
    for j,by in enumerate(BAY_Y):
        dz=z-1.92
        upper=ramp((dz+.38)/.88)
        width=.24+.25*np.clip(dz,0,2.20)
        axis=by+.095*dz+.085*np.sin(3.3*dz+j)+.075*cloud
        col=np.exp(-((y-axis)/width)**2)*upper
        cap=field(z,y,3.70,by+.17,.41,.83)
        black=np.maximum(black,(.78*col+.22*cap)*(.91+.42*cloud))
    ash=np.clip(.46*black+.30*streak*ramp((black-.04)/.43)+.15*cloud,0,1)
    fade=ramp((.5-np.abs(u-.5))/.105)*ramp((.5-np.abs(v-.5))/.12)
    save('Wall',black,ash,.83+.1*cloud,fade*np.clip(.84*black+.18*ash,0,.90))

def apron():
    w,h=2048,2048
    u,v=axes(w,h)
    x,y=2.90+(u-.5)*10.20,(v-.5)*7.80
    fine=noise(w,h,350,290,31)
    grain=noise(w,h,910,760,78)
    coarse=noise(w,h,44,32,924)
    broken=.66*fine+.34*coarse
    furrows=[tread(x,y,line,.021*coarse) for line in cart_wheelways()]
    distance=.115-np.maximum(*furrows)
    rut=np.exp(-((distance+.012*broken)/.049)**2)
    lip=np.exp(-((distance-.085-.018*broken)/.029)**2)
    drip=np.exp(-((x+1.90-.043*coarse)/.12)**2)*ramp((3.67-np.abs(y))/.31)
    ash=np.zeros((h,w),'f')
    grit=ash.copy()
    for by in BAY_Y:
        bx,_=bay(by)
        ash=np.maximum(ash,.86*field(x,y,bx-.67,by,.88,.60)+.31*field(x,y,bx-1.44,by-.21,1.01,.31))
        grit+=.37*field(x,y,bx-.65,by+.70,.94,.22)
    ash=np.clip(ash*(.87+.52*broken)+.30*grit,0,1)
    # Alternating heel and forefoot prints on the fuel run and the turn off the cart lane.
    prints=np.zeros((h,w),'f')
    rng=random.Random(61123)
    def trail(points):
        rest=0.
        s=1
        for a,b in zip(points,points[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            ux,uy=dx/length,dy/length
            while rest<length:
                cx=a[0]+rest*ux-.097*s*uy
                cy=a[1]+rest*uy+.097*s*ux
                # Only evaluate the cropped sole region.
                i0=max(0,int((cx+2.20-.23)/10.20*w)); i1=min(w,int((cx+2.20+.23)/10.20*w)+1)
                j0=max(0,int((cy+3.90-.23)/7.80*h)); j1=min(h,int((cy+3.90+.23)/7.80*h)+1)
                xx=x[:,i0:i1]-cx
                yy=y[j0:j1,:]-cy
                yaw=math.atan2(uy,ux)+rng.uniform(-.26,.26)
                c,d=math.cos(yaw),math.sin(yaw)
                t=c*xx+d*yy; n=-d*xx+c*yy
                width=.045*rng.uniform(.90,1.18)
                fore=np.exp(-(((t-.051)/.093)**2+(n/width)**2)**2)
                heel=np.exp(-(((t+.095)/.039)**2+(n/(width*.84))**2)**2)
                stamp=np.maximum(fore,heel)*rng.uniform(.38,.91)
                area=prints[j0:j1,i0:i1]
                np.maximum(area,stamp,out=area)
                rest+=rng.uniform(.46,.73)
                s=-s
            rest-=length
    trail([(.61,-2.19),(2.15,-1.11),(4.53,-.38),(6.18,-.81),(5.97,.48),(6.14,1.42)])
    trail([(2.0,3.64),(2.15,2.58),(3.47,1.26),(4.83,1.10),(6.05,1.57)])
    damp=np.clip(.81*rut+.74*drip+.69*prints*(.78+.32*fine)+.21*field(x,y,2.13,2.84,.85,.40),0,1)
    swarf=field(x,y,.62,-2.17,1.27,.34)*ramp((grain+.18)/.73)
    pale=np.clip(.58*lip+.42*swarf+grit+.29*ash*(.66+grain)+.17*prints,0,1)
    opacity=np.clip(.70*ash+.71*damp+.49*pale,0,.91)*(.85+.15*broken)
    edge=ramp((.5-np.abs(u-.5))/.038)*ramp((.5-np.abs(v-.5))/.047)
    save('Apron',ash,damp,pale,opacity*edge)

if __name__=='__main__':
    roof()
    wall_bloom()
    apron()
