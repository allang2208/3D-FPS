"""New finish textures authored as production material data; no reference image edits."""
from pathlib import Path
import numpy as np,json
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';TEX=OUT/'Textures';TEX.mkdir(parents=True,exist_ok=True)
N=2048;R=np.random.default_rng(9211934);recipes={}
def noise(n):return (np.asarray(Image.fromarray(R.integers(0,256,(n,n),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)-128)/128
macro=noise(11);mid=noise(129);micro=noise(1500)
strokes=Image.new('L',(N,N),0);d=ImageDraw.Draw(strokes)
for i in range(280):
    x=int(R.integers(N));y=int(R.integers(N));d.line((x,y,x+int(R.integers(-3,4)),y+int(R.integers(9,100))),fill=int(R.integers(20,120)),width=1)
scratch=np.asarray(strokes,dtype=np.float32)/255
grain=np.broadcast_to(R.normal(0,.6,(N,1)),(N,N)).astype(np.float32)
def finish(key,base,rough,metal,height,variation):
    c=np.clip(np.array(base)[None,None,:]+variation[:,:,None],0,255).astype('uint8')
    dy,dx=np.gradient(height);n=np.dstack((-dx*2,-dy*2,np.ones_like(dx)));n/=np.linalg.norm(n,axis=2)[:,:,None]
    maps={}
    for channel,arr in [('BaseColor',c),('Roughness',(np.clip(rough,0,1)*255).astype('uint8')),('Normal',((n*.5+.5)*255).astype('uint8'))]:
        p=TEX/(key+'_'+channel+'.png');Image.fromarray(arr).save(p);maps[channel]=str(p)
    recipes[key]={'maps':maps,'metallic':metal}
finish('Machined',[150,153,151],.29+.045*macro+.016*mid+scratch*.10,.94,micro*.002+grain*.003-scratch*.012,macro*3+grain*.8-scratch*9)
finish('Forged',[114,119,115],.41+.06*macro+.025*mid,.91,micro*.006+mid*.005-scratch*.012,macro*5+mid*2-scratch*11)
finish('CastGreen',[63,78,70],.59+.05*macro+.03*mid,0,micro*.015+mid*.008,macro*3+mid*1.0)
finish('RubberGrip',[28,33,30],.63+.05*macro+.02*mid,0,micro*.007,macro*2+mid*.6)
finish('RedGrip',[100,43,30],.43+.04*macro+.02*mid,0,micro*.003,macro*3+mid*.6)
recipes['Reflector']={'color':[.63,.67,.63],'roughness':.29,'metallic':.2}
(OUT/'material-manifest.json').write_text(json.dumps(recipes,indent=2),encoding='utf-8')
print('SCULPT_SURFACES_AUTHORED',len(recipes))
