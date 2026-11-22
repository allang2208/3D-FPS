"""Paint wear, rain tracks, oak end checks and worn fasteners, one atlas half per sign face."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageBlacksmith20261117'
out=source/'ForgeR2'
n=1024
y,x=np.mgrid[0:n,0:n].astype(np.float32)/(n-1)
def noise(rng,h,w):
    return np.asarray(Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC),dtype=np.float32)/255
def mix(a,b,k):return a*(1-k[...,None])+b*k[...,None]
def byte(v):return np.uint8(255*np.clip(v,0,1))
def grain(side,pigment):
    rng=np.random.default_rng(7300+side)
    outline=Image.new('L',(n,n));p=[(0,0),(1,0),(1,.77),(.92,.87),(.77,.94),(.58,.99),(.50,1),(.38,.99),(.20,.94),(.09,.87),(0,.77)]
    ImageDraw.Draw(outline).polygon([(int(.5+a*(n-2)),int(.5+b*(n-2))) for a,b in p],fill=255)
    edge=distance_transform_edt(np.asarray(outline)>0)/n
    broad=noise(rng,9,19); fib=noise(rng,56,780); fine=noise(rng,440,900);wash=noise(rng,24,93)
    waves=x+.012*np.sin(8*y+x*13+side)+.0035*np.sin(18*y+x*23)
    knots=np.zeros_like(x)
    for kx,ky in ([(.205,.64),(.522,.19),(.855,.79)] if not side else [(.13,.31),(.54,.67),(.88,.48)]):
        dx=(x-kx);dy=(y-ky)*.40
        rad=np.hypot(dx,dy)
        waves+=.030*np.sign(dx)*np.exp(-(rad/.058)**2)
        knots+=np.exp(-(rad/.029)**2)*(.53+.47*np.cos(330*rad)**2)
    late=(.5+.5*np.cos(403*waves+4.3*broad))**7
    pore=np.clip((.55-fib)*3.4,0,1)**2
    lines=np.zeros_like(x)
    for _ in range(34):
        xx=rng.uniform(.01,.99);top=rng.random()<.48
        start=rng.uniform(.015,.14) if top else rng.uniform(.67,.93)
        length=rng.uniform(.045,.24)
        lane=xx+.0028*np.sin(22*y+xx*30)+.0008*np.sin(130*y+xx)
        phase=(y-start)/length
        lines=np.maximum(lines,np.exp(-((x-lane)/.00165)**2)*np.clip(1-(2*phase-1)**2,0,1))
    # Hanger positions reverse on the opposing face. Runoff tapers with distance below each saddle.
    rail=(.177,.823) if side==0 else (.171,.819)
    rust=np.zeros_like(x);rub=np.zeros_like(x)
    for u in rail:
        dx=x-u-.003*np.sin(y*28)
        rust+=np.exp(-(dx/(.008+.011*np.exp(-y*13)))**2)*np.exp(-y*10)*(.48+.52*fib)
        rub=np.maximum(rub,np.exp(-((x-u)/.034)**2-((y-.054)/.052)**2))
    joint=np.minimum(abs(x-(.322 if not side else .327)),abs(x-(.675 if not side else .678)))
    priority=.66*np.exp(-edge/.024)+.35*np.exp(-joint/.012)+.42*rub+.18*y**3
    chip=np.clip((.52*wash+.25*fib+.23*fine+priority*.65-.70)*6.4,0,1)
    retention=np.clip(.91-.16*late-.14*pore-.9*chip-.64*lines-.13*knots-.09*broad,0,1)
    timber=mix(np.array([.37,.275,.177]),np.array([.59,.46,.30]),broad)
    timber*=np.clip(1.12-.28*late-.22*pore-.39*knots-.36*lines,.32,1.1)[...,None]
    bleached=np.clip(.5*chip+.16*y**3-.35*rust,0,.63)
    timber=mix(timber,np.array([.58,.515,.423]),bleached)
    pigment=pigment*(.94+.12*broad-.12*late-.06*pore)[...,None]
    color=mix(timber,pigment,retention)
    color=mix(color,np.array([.27,.138,.073]),np.clip(rust*.81,0,.75))
    height=.24*broad-.16*late-.13*pore-.27*knots-.39*lines+.12*retention-.13*chip
    dy,dx=np.gradient(gaussian_filter(height,.85))
    normal=np.stack([-dx*3.9,-dy*3.9,np.ones_like(dx)],axis=2)
    normal/=np.linalg.norm(normal,axis=2)[...,None]
    rough=np.clip(.69+.14*retention+.08*pore+.12*chip-.25*rub,.43,.97)
    ao=np.clip(.99-.19*lines-.13*pore-.14*knots-.14*np.exp(-joint/.003),.48,1)
    return byte(color),byte(.5+.5*normal),byte(np.stack([ao,rough,np.zeros_like(ao)],axis=2))
if __name__=='__main__':
    emblem=np.asarray(Image.open(source/'TradeSign/T_SmithTradeSign_Pigment.png').convert('RGB'),dtype=np.float32)/255
    g,b=emblem[:,:,1],emblem[:,:,2]
    pigment=mix(np.array([.505,.220,.151]),np.array([.842,.772,.62]),g)
    pigment=mix(pigment,np.array([.70,.50,.24]),b)
    pigment=mix(pigment,np.array([.25,.23,.20]),np.minimum(g,b))
    a,b=grain(0,pigment),grain(1,pigment)
    for i,key in enumerate(('Color','NormalDX','ORM')):
        Image.fromarray(np.concatenate([a[i],b[i]],axis=1)).save(out/('T_SmithWeatheredOak_'+key+'.png'))
