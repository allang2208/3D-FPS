"""Project-authored Boss PBR textures. Physical surface detail, no external imagery."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(exist_ok=True)
N=1024;rng=np.random.default_rng(922410)

def noise(grid):
    data=rng.random((grid,grid)).astype(np.float32)
    t=np.arange(N,dtype=np.float32)*grid/N;i=t.astype(int);f=t-i;f=f*f*(3-2*f)
    a=data[i[:,None]%grid,i[None,:]%grid];b=data[i[:,None]%grid,(i[None,:]+1)%grid]
    c=data[(i[:,None]+1)%grid,i[None,:]%grid];d=data[(i[:,None]+1)%grid,(i[None,:]+1)%grid]
    return (a*(1-f)[None,:]+b*f[None,:])*(1-f)[:,None]+(c*(1-f)[None,:]+d*f[None,:])*f[:,None]

def write(name,channel,array):
    p=OUT/(name+'_'+channel+'.png');Image.fromarray(np.uint8(np.clip(array,0,1)*255)).save(p);return str(p)

def surface(name,color,rough,metal,kind):
    n1,n2,n3,n4=noise(4),noise(24),noise(96),noise(350)
    concrete=kind=='concrete';variation=(n1-.5)*(.22 if concrete else .12)+(n2-.5)*.07+(n3-.5)*.04
    rgb=np.array(color,dtype=np.float32)[None,None,:]/255*(1+variation[:,:,None])
    chips=np.maximum(0,(n3-.80)*5)*np.maximum(0,(n2-.58)*3) if not concrete else np.zeros((N,N))
    pores=np.clip((n4-.79)*7,0,1)*(0.3+0.7*n2) if concrete else np.zeros((N,N))
    if concrete:rgb*=1-pores[:,:,None]*.55
    # Tiny pits and restrained chipped paint; heavier contact grime is authored on mesh vertices.
    rgb=rgb*(1-chips[:,:,None])+np.array([.19,.17,.12])[None,None,:]*chips[:,:,None]
    height=(n3-.5)*(.0016 if concrete else .00012)+(n4-.5)*(.0011 if concrete else .00008)-chips*.00035-pores*.0009
    gy,gx=np.gradient(height,2/N);normal=np.stack((-gx,gy,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    maps=dict(BaseColor=write(name,'BaseColor',rgb),Roughness=write(name,'Roughness',rough+(n2-.5)*.11+(n4-.5)*.04),
        Metallic=write(name,'Metallic',np.full((N,N),metal)+(1-metal)*chips*.8),Normal=write(name,'Normal',normal*.5+.5))
    return dict(maps=maps,metallic=metal,normal_strength=.65,vertex_wear=kind=='paint',provenance='Deterministic project-authored physical PBR')

specs={}
for name,color,rough,metal,kind in [
 ('BossMachinePaint',(74,84,58),.55,.04,'paint'),
 ('BossStructuralSteel',(59,66,58),.64,.12,'paint'),
 ('BossGrating',(85,91,86),.47,.78,'metal'),
 ('BossFloor',(111,109,99),.79,0,'concrete'),
 ('BossFoundation',(135,130,115),.84,0,'concrete'),
 ('BossWetConcrete',(75,77,65),.23,0,'concrete')]:specs[name]=surface(name,color,rough,metal,kind)
for key in ('BossFloor','BossFoundation'):specs[key]['vertex_wear']=True
# Puddle uses the same concrete grain, with authored wetness fading across the outer ring.
specs['BossWetConcrete']=dict(specs['BossFloor'],vertex_wetness=True)
font_path=Path('C:/Windows/Fonts/arial.ttf')
def font(size):return ImageFont.truetype(str(font_path),size)
im=Image.new('RGB',(512,512),(215,207,173));d=ImageDraw.Draw(im)
for i in range(61):
    a=math.radians(140+i*260/60);r0=192 if i%10==0 else 207 if i%5==0 else 216;r1=233
    xy=[(256+r*math.cos(a),256+r*math.sin(a)) for r in (r0,r1)];d.line(xy,fill=(29,33,28),width=4 if i%5==0 else 2)
    if i%10==0:d.text((256+163*math.cos(a),256+163*math.sin(a)),str(i//10),font=font(25),fill=(35,37,30),anchor='mm')
d.text((256,185),'MPa',font=font(30),fill=(35,37,30),anchor='mm');d.text((256,332),'CLASS 1.6',font=font(19),fill=(55,56,43),anchor='mm')
path=OUT/'BossGauge_BaseColor.png';im.save(path)
specs['BossGauge']=dict(maps={'BaseColor':str(path)},metallic=0,roughness=.42)
im=Image.new('RGB',(1024,512),(151,153,136));d=ImageDraw.Draw(im)
d.rounded_rectangle((12,12,1011,499),24,outline=(53,60,48),width=14)
for txt,y,size in [('PUMP DIVISION',80,64),('INDUSTRIAL WATER SYSTEM',162,40),('MODEL  RP-240   |   55 kW',252,48),('1450 RPM   /   SERVICE 04',333,44),('ISOLATE POWER BEFORE SERVICE',414,36)]:
    d.text((512,y),txt,font=font(size),fill=(32,40,30),anchor='mm')
path=OUT/'BossLabel_BaseColor.png';im.save(path)
specs['BossLabel']=dict(maps={'BaseColor':str(path)},metallic=.65,roughness=.48)
from service_materials import extend
extend(specs,noise,write,N)
catalog=dict(version=3,materials=specs,normal_convention='OpenGL tangent; flip green on Unreal import',
    vertex_color='ServiceAge R=contact grime; G=pipe corrosion for pipe recipes, exposed edge for other paint; B=wet floor',textures_source='Project authored; no third party imagery',tests_run=False)
(ROOT/'Authored/polish-materials.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
print('BOSS_PBR_AUTHORED',len(specs),'materials')
