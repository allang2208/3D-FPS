"""Centimetre-scale woven, stitched and leather fields shared by bake and high mesh."""
import numpy as np

def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)

def line(x,y,path,width=.035):
    distance=np.full_like(x,1.e4)
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy),0,1)
        distance=np.minimum(distance,np.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
    return np.exp(-(distance/width)**2)

def evaluate(v):
    x,y,back,hand,digit,dt,arc,seam=np.moveaxis(v,-1,0)
    cuff=1-smooth(-.5,.35,y);cloth=np.clip(back*.98+cuff*(1-back),0,1)
    # Each digit's weave uses its own longitudinal and circumferential fields.
    mx=x*(1-digit)+seam*digit;my=y*(1-digit)+arc*digit
    warp=np.cos(mx*2*np.pi/.043);weft=np.cos(my*2*np.pi/.043)
    weave=.0015*(warp+weft)+.0006*np.cos(mx*np.pi/.043)*np.cos(my*np.pi/.043)
    grain=.0016*np.sin(mx*64+np.sin(my*27))*np.sin(my*78+np.cos(mx*21))
    star=[]
    for i in range(16):
        a=i*np.pi/8;r=1.42 if i%4==0 else 1. if i%2==0 else .35
        star.append((-.55+r*np.sin(a),4.55+r*np.cos(a)))
    emb=line(x,y,star+[star[0]],.040)
    for sign in (-1,1):
        yy=np.linspace(.15,7.6,55);xx=-.55+sign*(2.30+.25*np.sin(yy*1.2))
        emb=np.maximum(emb,line(x,y,list(zip(xx,yy)),.033))
        for z in (1.,2.5,6.1,7.1):
            a=-.55+sign*(2.30+.25*np.sin(z*1.2));path=[(a,z),(a+sign*.48,z+.24),(a+sign*.62,z+.58),(a+sign*.19,z+.43),(a,z)]
            emb=np.maximum(emb,line(x,y,path,.032))
    emb*=back*hand*smooth(-.1,.8,y)
    cuff_edge=(np.exp(-((y+2.65)/.045)**2)+np.exp(-((y+.85)/.045)**2))*cuff
    cuff_vine=np.exp(-((y-(-1.7+.22*np.sin(x*2.1)))/.036)**2)*cuff
    thread=np.maximum(emb,np.clip(cuff_edge+cuff_vine,0,1))
    side=np.exp(-((seam+.12)/.028)**2)*digit
    stitch=side*(.65+.35*np.cos(arc*np.pi*8)**4)
    ring=np.exp(-((dt-.21)/.025)**2)*digit*back*.40
    palmseam=line(x,y,[(-3.1,6.5),(-1.5,6.0),(.3,6.1),(1.7,6.8)],.04)*(1-back)*hand
    palmseam=np.maximum(palmseam,line(x,y,[(2.3,2.),(1.45,3.1),(.1,4.05),(-2.4,4.25)],.035)*(1-back)*hand)
    thread=np.clip(np.maximum(thread,stitch+ring),0,1)
    h=weave*cloth+grain*(1-cloth)+thread*.014-palmseam*.014
    h-=digit*back*(.008*np.exp(-((dt-.08)/.06)**2)+.006*np.exp(-((dt-.86)/.05)**2))
    blue=np.array([.07,.22,.55]);navy=np.array([.035,.065,.115]);silver=np.array([.69,.67,.61])
    modulation=.96+.025*(warp+weft)
    color=(navy*(1-cloth[...,None])+blue*cloth[...,None])*modulation[...,None]
    color*=1-cuff[...,None]*np.array([.45,.45,.35]);color=color*(1-thread[...,None])+silver*thread[...,None]
    color*=1-palmseam[...,None]*.18
    rough=.58*(1-cloth)+.85*cloth;rough=rough*(1-thread)+.53*thread
    ao=np.clip(1-palmseam*.12-np.maximum(-h,0)*3,.84,1)
    return dict(height=h,color=color,rough=rough,ao=ao,fuzz=cloth*(1-thread)*.55)
