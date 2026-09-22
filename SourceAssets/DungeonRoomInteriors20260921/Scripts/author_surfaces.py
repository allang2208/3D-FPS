"""Author physical surface maps for the room meshes; no scene preview."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=np.random.default_rng(921254);S=2048
y,x=np.mgrid[0:S,0:S].astype(np.float32)

def noise(scale):
    a=N.integers(0,256,(max(2,S//scale),max(2,S//scale)),dtype=np.uint8)
    return np.array(Image.fromarray(a).resize((S,S),Image.Resampling.BICUBIC),np.float32)/255

fine=noise(2);medium=noise(17);macro=noise(230)
manifest={}
def save(name,tint,variation,rough,height,strength,metal=0):
    color=np.array(tint,np.float32)[None,None,:]+variation[:,:,None]
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    maps={'BaseColor':np.uint8(np.clip(color,0,255)),
          'Roughness':np.uint8(np.clip(rough,0,1)*255),
          'Normal':np.uint8(np.clip(normal*.5+.5,0,1)*255)}
    manifest[name]={'metallic':metal,'maps':{}}
    for ch,a in maps.items():
        path=OUT/(name+'_'+ch+'.png');Image.fromarray(a).save(path)
        manifest[name]['maps'][ch]=str(path)

grain=np.sin(y*.58+np.sin(x*.008)*1.5+medium*1.2)*.5+.5
latewood=np.clip((grain-.66)*3,0,1)
woodvar=(macro-.5)*9+(medium-.5)*7+(fine-.5)*3-latewood*13
save('Timber',(125,99,70),woodvar,.71+medium*.16,latewood*.07+fine*.012,1.2)
for name,tint in [('GreenPaint',(67,79,70)),('RedPaint',(112,54,39)),('YellowPaint',(159,119,45))]:
    save(name,tint,(macro-.5)*4+(medium-.5)*3+(fine-.5)*2,.54+medium*.13,fine*.01+medium*.009,.7,.06)
save('Iron',(78,81,77),(medium-.5)*11+(fine-.5)*5,.39+medium*.24,fine*.025,1.1,.82)
save('Rust',(90,62,41),(medium-.5)*17+(fine-.5)*6,.79+medium*.14,medium*.045+fine*.05,1.9)
save('OldStone',(137,128,109),(macro-.5)*9+(medium-.5)*12+(fine-.5)*5,.82+medium*.11,medium*.12+fine*.05,1.6)
save('Soil',(91,77,57),(macro-.5)*8+(medium-.5)*9+(fine-.5)*12,.91+medium*.07,medium*.09+fine*.08,2.0)
weave=(np.sin(x*2.4)*np.sin(y*2.4)+1)*.5
save('Canvas',(140,131,105),(macro-.5)*8+(medium-.5)*6+(weave-.5)*6,.91+medium*.06,weave*.017,.8)
save('Rubber',(34,38,35),(medium-.5)*3+(fine-.5)*2,.77+medium*.09,fine*.014,.8)
(OUT.parent/'material-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('ROOM_SURFACES_AUTHORED',len(manifest))
