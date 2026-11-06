"""Steel finishes on a rail-aligned UV atlas. Reflections come from the actual grind."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

OUT=Path(__file__).resolve().parent/'Textures'
OUT.mkdir(exist_ok=True)
W,H=1024,4096
u=(np.arange(W,dtype=np.float32)[None,:]+.5)/W
z=(1.-(np.arange(H,dtype=np.float32)[:,None]+.5)/H-.02)*1.10/.96
p=abs((u-.41)/.39)
def ease(a,b,x):
    f=np.clip((x-a)/(b-a),0,1)
    return f*f*(3-2*f)
def mix(a,b,t):
    return a*(1.-t)+b*t
blue=ease(.224,.270,p)*(1-ease(.362,.423,p))*(1-ease(.50,.74,z))*ease(.023,.057,z)
leaf=(1-ease(.135,.175,p))*(1-ease(.255,.285,z))*ease(.030,.055,z)
facet=ease(.67,.69,p)
silver=(u>.822)&(u<.928)
bronze=u>=.928
rng=np.random.default_rng(605)
grain=rng.normal(0,1,(H,W)).astype(np.float32)
long=cv2.GaussianBlur(grain,(3,35),.50,sigmaY=6)
cloud=cv2.resize(rng.normal(0,1,(60,20)).astype(np.float32),(W,H),interpolation=cv2.INTER_CUBIC)
drag=np.zeros((H,W),np.float32)
for i in range(1050):
    x,y=map(int,[rng.integers(W),rng.integers(H)])
    cv2.line(drag,(x,y),(x+int(rng.integers(-5,5)),y+int(rng.integers(5,58))),float(rng.uniform(.08,.74)),1)
def save(key,values):
    Image.fromarray(np.uint8(np.clip(values,0,255))).save(OUT/('T_RidgeWedge_'+key+'.png'))
tones=[]
for i,(steel,lane,bed,wire,gold) in enumerate(zip((160,164,167),(47,61,72),(83,84,84),(209,210,208),(156,132,96))):
    face=mix(steel+facet*9,lane,blue)
    face=mix(face,bed,leaf)
    face=mix(mix(face,wire,silver),gold,bronze)
    tones.append(face+1.3*cloud+2.1*long+grain*.20-drag*3)
save('BaseColor',np.stack(tones,axis=-1))
rough=.375+.065*blue+.035*leaf-.067*facet
save('Roughness',255*(mix(mix(rough,.29,silver),.34,bronze)+.012*cloud+.013*long+.025*drag))
# R is metal, G is engraved light, B protects the inserted metals and recessed
# finish when the player selects a different alloy for the blade faces.
ink=ease(.283,.294,p)*(1-ease(.303,.315,p))*ease(.027,.069,z)*(1-ease(.30,.46,z))
metal=np.broadcast_to(247.-6*blue-3*leaf,(H,W))
protected=np.maximum(np.maximum(.76*blue,.48*leaf),silver|bronze)
save('Metallic',np.stack((metal,255*ink,255*protected),axis=-1))
dy,dx=np.gradient(.06*long+.09*drag)
save('Normal',np.stack((128.-43*dx,128.+22*dy,np.full_like(dx,255.)),axis=-1))
