"""Physical-scale PBR: fine insulation, anisotropic brushed titanium and copper."""
from pathlib import Path
from PIL import Image,ImageFilter,ImageDraw
import numpy as np,json
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(exist_ok=True)
rng=np.random.default_rng(20261031);S=2048
def noise(nx,ny):
    return np.asarray(Image.fromarray(rng.integers(0,256,(ny,nx),dtype=np.uint8)).resize((S,S),Image.Resampling.BICUBIC),dtype=np.float32)/255-.5
micro=noise(S,S);fine=noise(420,420);broad=noise(23,23)
y,x=np.mgrid[0:S,0:S].astype(np.float32)/S
receipt=[]
for family in ('Rubber','Titanium','Copper'):
    if family=='Rubber':
        # Tens of micrometres of stipple over woven, non-directional insulation.
        weave=np.sin((x+y)*2*np.pi*145)*np.sin((x-y)*2*np.pi*145)
        height=.000010*weave+.000016*fine+.000006*micro
        color=np.array([.075,.089,.105],np.float32)
        base=color[None,None,:]*(1+.09*broad[...,None]+.08*fine[...,None])
        rough=.66+.07*fine+.035*broad;metal=np.zeros((S,S),np.float32)
    else:
        brush=noise(1500,12)
        scratches=Image.new('L',(S,S),0);d=ImageDraw.Draw(scratches)
        for i in range(430):
            xx=int(rng.integers(S));yy=int(rng.integers(S));length=int(rng.integers(9,85))
            d.line((xx,yy,xx+int(rng.integers(-2,3)),yy+length),fill=int(rng.integers(35,125)),width=1)
        sc=np.asarray(scratches.filter(ImageFilter.GaussianBlur(.3)),dtype=np.float32)/255
        height=.000003*micro+.000005*brush-.000013*sc
        color=np.array([.19,.225,.265] if family=='Titanium' else [.62,.35,.17],np.float32)
        base=color[None,None,:]*(1+.045*broad[...,None]+.04*brush[...,None])
        rough=(.34 if family=='Titanium' else .28)+.045*brush+.10*sc+.018*fine
        metal=np.full((S,S),.94 if family=='Titanium' else .97,np.float32)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*.065/S)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*.065/S)
    n=np.stack((-dx,dy,np.ones_like(height)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    orm=np.stack((np.clip(1+.025*fine,.96,1),np.clip(rough,.05,1),metal),axis=-1)
    for kind,arr in [('BaseColor',base),('ORM',orm),('Normal',n*.5+.5)]:
        name='T_Coil_'+family+'_'+kind+'.png'
        Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).save(T/name)
        receipt.append(dict(file=name,size=[S,S],role=kind))
    Image.fromarray(np.uint16(np.clip((height+.00004)/.00008,0,1)*65535)).save(T/('H_Coil_'+family+'_Source16.png'))
(P/'texture_manifest.json').write_text(json.dumps(dict(size_m=.065,normal='OpenGL; UE flip green',maps=receipt),indent=2),encoding='utf-8')
print('COIL_PBR_SAVED',len(receipt))
