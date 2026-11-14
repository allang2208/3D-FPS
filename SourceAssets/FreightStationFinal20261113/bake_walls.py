"""Unique registered surface atlases, from the existing mineral scans, in centimeters."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,gaussian_filter
from functools import lru_cache
R=Path(__file__).resolve().parent
P=R.parent/'DungeonWallUpgrade20260924/Authored/Textures'
D=R.parent/'FacilityQuixel20261108/Sources/DamagedConcrete/Textures'
O=R/'Textures';O.mkdir(exist_ok=True)
env={'__file__':str(R.parent/'FreightOppositePlatform20261113/bake_surfaces.py')}
exec(compile((R.parent/'FreightOppositePlatform20261113/bake_surfaces.py').read_text('utf8').split('def wall(')[0],'mask_helpers','exec'),env)
field,step,distress=env['field'],env['step'],env['distress']
@lru_cache(16)
def pixels(path):
    a=np.asarray(Image.open(path).convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS),dtype='f')/255
    return a
def sample(path,U,V):
    a=pixels(path);xy=np.stack([np.mod(V,1)*1023,np.mod(U,1)*1023])
    return np.stack([map_coordinates(c,xy,order=1,mode='wrap') for c in a.transpose(2,0,1)],axis=-1)
def emit(name,img):Image.fromarray(np.uint8(np.clip(img,0,1)*255+.5)).save(O/('T_'+name+'.png'),compress_level=2)
def power(size):return min(4096,max(256,2**math.ceil(math.log2(max(1,size/.75)))))
def bake(key,s):
    width=s['hi']-s['lo'];height=s['z1']-s['z0']
    W,H=power(width),min(2048,power(height));shape=(H,W);rng=np.random.default_rng(s['seed'])
    x,z=np.meshgrid(s['lo']+(np.arange(W,dtype='f')+.5)*width/W,s['z1']-(np.arange(H,dtype='f')+.5)*height/H)
    macro=field(rng,shape,max(3,int(width/190)),max(3,int(height/210)))
    medium=field(rng,shape,max(5,int(width/32)),max(4,int(height/34)))
    fine=field(rng,shape,max(8,int(width/3)),max(8,int(height/3)))
    streak=field(rng,shape,max(4,int(width/19)),max(3,int(height/320)))
    offset=rng.uniform(0,2,4);blend=step(-.65,.72,macro*.75+medium*.36)
    U=x/186+offset[0];V=-z/186+offset[1];U2=x/239+offset[2];V2=-z/239+offset[3]
    a=sample(P/'Wall_BaseColor.png',U,V);b=sample(P/'Wall_BaseColor.png',U2,V2)
    base=(a*(1-blend[:,:,None])+b*blend[:,:,None]).mean(2)
    grit=sample(P/'FabSection_BaseColor.png',x/112+offset[2],-z/112+offset[0]).mean(2)
    col=.516+.79*(base-.53)+.46*(grit-.476)+.016*macro+.009*medium+.006*streak
    na=sample(P/'Wall_Normal.png',U,V)[:,:,:2]*2-1;nb=sample(P/'Wall_Normal.png',U2,V2)[:,:,:2]*2-1
    norm=.62*(na*(1-blend[:,:,None])+nb*blend[:,:,None])+.57*(sample(P/'FabSection_Normal.png',x/112+offset[2],-z/112+offset[0])[:,:,:2]*2-1)
    sa=sample(P/'Wall_ORM.png',U,V);sb=sample(P/'Wall_ORM.png',U2,V2)
    surf=sa*(1-blend[:,:,None])+sb*blend[:,:,None];rough=.61+.26*surf[:,:,1]+.018*medium
    clusters=[]
    # Short protected corners and footing stains. Upper fields deliberately stay quiet.
    if width>260 and s['kind']!='Pier':
        for edge in [s['lo']+rng.uniform(12,50),s['hi']-rng.uniform(16,46)]:
            if rng.random()<.72:clusters.append((edge,s['z0']+rng.uniform(9,26),rng.uniform(7,19),rng.uniform(5,16),rng.uniform(.62,.92)))
    loss=distress(x,z,clusters,medium,fine)
    core=sample(next(D.glob('*B-O.png')),x/137+offset[0],-z/137+offset[2]).mean(2)
    col=col*(1-loss)+(.38+.53*(core-.37)+.58*(grit-.48))*loss
    col+=.18*np.maximum(gaussian_filter(loss,.8)-loss,0)
    rough=rough*(1-loss)+(.86+.07*medium)*loss
    if width>850 and s['kind']=='Hall':
        anchor=s['lo']+width*rng.uniform(.19,.8);fall=(s['z1']-z)/max(1,height)
        run=np.exp(-((x-anchor-2.4*medium)/(8+8*fall))**2)*step(0,.06,fall)*(1-step(.34,.86,fall))
        col-=.042*run*(.67+.33*streak);rough-=.06*run
    norm[:,:,0]+=np.clip(np.gradient(loss,axis=1),-.5,.5)*.7
    norm[:,:,1]-=np.clip(np.gradient(loss,axis=0),-.5,.5)*.7
    nn=np.dstack((norm,np.ones_like(x)));nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    emit(key+'_Color',col[:,:,None]*np.array([1.023,1.005,.978],dtype='f'))
    emit(key+'_Normal',nn*.5+.5)
    emit(key+'_ORM',np.dstack((.86+.14*surf[:,:,0]-.1*loss,rough,np.zeros_like(x))))
    return [W,H]
out={}
for key,s in json.loads((R/'wall-plan.json').read_text('utf8')).items():
    out[key]=bake(key[10:],s)
(R/'texture-manifest.json').write_text(json.dumps(out,indent=1),'utf8')
print({'atlases':len(out),'textures':len(out)*3})
