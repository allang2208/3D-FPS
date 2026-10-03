"""Quiet snake scales following the longitudinal fitted skin UV frame."""
import math
import numpy as np

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def scale_fields(u,v,width=.046,height=.064):
    du=u-.5
    # v points upward in the atlas. Each scale's pointed negative-v tip therefore
    # runs from the grip shoulder toward the magwell, along the fitted spine.
    qx=du*(width/.0029)+9*du**3+.15*np.sin(v*math.tau)
    qy=v*(height/.00265)+.35*u+.12*np.sin(u*math.pi)
    row=np.floor(qy);best=np.zeros(np.broadcast_shapes(np.shape(u),np.shape(v)))
    lip=np.zeros_like(best);grain=np.zeros_like(best);variation=np.zeros_like(best)
    for dj in (-1,0,1):
        r=row+dj;stagger=np.mod(r,2)*.5;col=np.floor(qx-stagger)
        for di in (-1,0,1):
            c=col+di;seed=np.sin(c*127.1+r*311.7)*43758.5453;random=seed-np.floor(seed)
            lx=qx-(c+.5+stagger+.06*np.sin(c*3.1+r*4.7));ly=qy-(r+.5+.04*np.sin(c*4.3-r*1.7))
            lx=lx+.08*ly
            span=.45*np.where(ly>.10,np.sqrt(np.clip(1-((ly-.10)/.46)**2,0,1)),np.clip((ly+.61)/.71,0,1))
            edge=np.minimum(np.minimum(.56-ly,ly+.61),span-np.abs(lx));body=smooth(edge/.060)
            chosen=body>best;ridge=np.clip((.56-ly)/1.17,0,1)
            hatch=np.sin((lx*15+ly*10+random)*math.tau)
            lip=np.where(chosen,body*(.45+.55*ridge),lip);grain=np.where(chosen,hatch*body,grain)
            variation=np.where(chosen,random-.5,variation);best=np.maximum(best,body)
    # Keep the lower rear badge's physical size when the panel gets longer.
    badge=np.maximum(np.abs((u-.78)/(.0026/width)),np.abs((v-.18)/(.0034/height)))
    reserve=smooth((badge-.90)/.15)
    return best*reserve,lip*reserve,grain*reserve,variation
