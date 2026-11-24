"""Four authored finish swatches: oxide graphite, ridgeline, aged bronze, polished bronze lip."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

out=Path(__file__).resolve().parent/'Textures'
out.mkdir(exist_ok=True)
rng=np.random.default_rng(842013)
width,height=1536,1536
def noise(w,h):
    src=Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8))
    return np.asarray(src.resize((width,height),Image.Resampling.BICUBIC),dtype=float)/255.-.5
marble=noise(28,45)
patina=noise(110,136)
brush=noise(740,92)
grain=rng.normal(0,.55,(height,width))
y,x=np.mgrid[:height,:width]
fine=brush*.60+np.roll(brush,5,axis=1)*.4
rgb=np.empty((height,width,3))
orm=np.empty_like(rgb)
relief=.42*grain+.6*patina+.65*fine
for i,(base,rough,metal) in enumerate([((56,49,49),119,209),((71,65,63),112,218),((164,117,78),97,233),((193,148,99),82,241)]):
    sl=slice(i*width//4,(i+1)*width//4)
    signal=(marble[:,sl]*12+patina[:,sl]*12+fine[:,sl]*7+grain[:,sl]*4)
    tint=np.array([1.15,.94,.65]) if i>=2 else np.ones(3)
    rgb[:,sl]=base+signal[:,:,None]*tint
    orm[:,sl,:]=[255,rough,metal]
    orm[:,sl,1]+=marble[:,sl]*22+fine[:,sl]*27+grain[:,sl]*3
dy,dx=np.gradient(relief)
norm=np.stack((-dx*.11,dy*.11,np.ones_like(dx)),axis=-1)
norm/=np.linalg.norm(norm,axis=-1)[:,:,None]
for suffix,array in [('Color',rgb),('ORM',orm),('Normal',(norm*.5+.5)*255)]:
    Image.fromarray(array.clip(0,255).astype('uint8')).save(out/f'T_Eclipse_{suffix}.png')
