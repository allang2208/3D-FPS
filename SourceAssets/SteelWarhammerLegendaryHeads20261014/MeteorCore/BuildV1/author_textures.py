"""Author coherent PBR and emissive masks for the enclosed meteor core and bronze."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(261015)
def noise(h,w,scale):
    a=rng.standard_normal((h,w));fy=np.fft.fftfreq(h)[:,None];fx=np.fft.rfftfreq(w)[None,:]
    f=np.fft.irfft2(np.fft.rfft2(a)/(1+scale*(fx*fx+fy*fy))**1.6,s=(h,w))
    return (f-f.mean())/(f.std()+1e-8)
def save(name,array):
    Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(T/(name+'.png'))
def normal(height,strength):
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    n=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n*.5+.5
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

# Periodic longitude, irregular branching cell edges and sparse hot channels.
H=W=2048;v,u=np.mgrid[0:H,0:W].astype(np.float64);u/=W;v/=H
coarse=noise(H,W,60000);fine=noise(H,W,240);micro=noise(H,W,4)
px=u*14+.32*np.sin(u*math.tau*3+v*math.tau*2)+.12*np.sin(v*math.tau*13+u*math.tau*7)
py=v*10+.30*np.cos(u*math.tau*4-v*math.tau*3)+.10*np.sin(u*math.tau*11+v*math.tau*5)
ix=np.floor(px);iy=np.floor(py);f1=np.full_like(u,99.);f2=f1.copy()
for dy in (-1,0,1):
    for dx in (-1,0,1):
        cx=ix+dx;cy=iy+dy
        hx=np.mod(np.sin(np.mod(cx,14)*127.1+np.mod(cy,10)*311.7)*43758.5453,1)
        hy=np.mod(np.sin(np.mod(cx,14)*269.5+np.mod(cy,10)*183.3)*26931.1241,1)
        d=np.sqrt((px-cx-.15-.7*hx)**2+(py-cy-.15-.7*hy)**2)
        smaller=d<f1;f2=np.where(smaller,f1,np.minimum(f2,d));f1=np.minimum(f1,d)
edge=f2-f1;crack=1-smooth(.012,.052,edge)
activity=smooth(-.6,.9,.70*np.sin(u*math.tau*3+v*math.tau*2)+.50*np.cos(v*math.tau*4-u*math.tau*2)+coarse*.35)
hot=crack*activity
height=.24*coarse+.14*fine+.035*micro-.75*crack
gray=np.clip(.095+.022*coarse+.024*fine+.007*micro-.055*crack,.015,.24)
base=np.stack((gray*1.07,gray,gray*.95),axis=-1)
rough=np.clip(.72+fine*.05+.10*crack-.25*hot,.40,.92)
ao=np.clip(1-crack*.45-f1*.10,.35,1)
save('T_MeteorCore_BaseColor',base)
save('T_MeteorCore_ORM',np.stack((ao,rough,np.clip(.18+fine*.025,0,.35)),axis=-1))
save('T_MeteorCore_Normal',normal(height,1.1))
save('T_MeteorCore_Heat',np.stack((hot,np.mod(u*.8+v*.3+coarse*.09,1),crack),axis=-1))

# Hammered bronze; broad roughness variation plus restrained fine scratches.
def bronze(h,w,glyph=None):
    a=noise(h,w,7000);b=noise(h,w,60);c=noise(h,w,3)
    height=a*.08+b*.08+c*.02
    if glyph is None:glyph=np.zeros((h,w))
    height-=glyph*.65
    value=np.clip(.70+a*.04+b*.035+c*.012,.45,.9)
    color=value[...,None]*np.array([.44,.285,.12])
    color*=1-glyph[...,None]*.72
    rough=np.clip(.43+b*.05+glyph*.18,.28,.75)
    return color,normal(height,1.35),np.stack((1-glyph*.25,rough,np.full((h,w),.94)),axis=-1)
for key,array in zip(('BaseColor','Normal','ORM'),bronze(1024,1024)):save('T_MeteorBronze_'+key,array)

# Each of 8 flat belt panels contains three different shallow celestial engravings.
# Texture rows follow circumference; columns follow the physical band width.
h,w=2048,512;canvas=Image.new('L',(w,h));draw=ImageDraw.Draw(canvas)
def line(points,width=5):draw.line(points,fill=255,width=width,joint='curve')
for row in range(24):
    cx=w*.5;cy=(row+.5)*h/24;rx=148;ry=29;kind=row%6
    if kind in (0,1):
        draw.ellipse((cx-rx*.48,cy-ry*.48,cx+rx*.48,cy+ry*.48),outline=255,width=5)
        if kind==0:
            for j in range(8):
                a=j*math.tau/8;line([(cx+rx*.65*math.cos(a),cy+ry*.65*math.sin(a)),(cx+rx*math.cos(a),cy+ry*math.sin(a))])
        else:line([(cx-rx*.32,cy),(cx+rx*.32,cy)]);line([(cx,cy-ry*.32),(cx,cy+ry*.32)])
    elif kind==2:
        line([(cx-rx*.75,cy-ry),(cx,cy+ry),(cx+rx*.75,cy-ry)])
        line([(cx-rx*.72,cy),(cx+rx*.72,cy)])
    elif kind==3:
        line([(cx,cy-ry),(cx,cy+ry)])
        for off in (-.5,0,.5):line([(cx-rx*.65,cy+off*ry),(cx+rx*.65,cy+off*ry)])
    elif kind==4:
        line([(cx,cy-ry),(cx+rx,cy),(cx,cy+ry),(cx-rx,cy),(cx,cy-ry)])
        line([(cx-rx*.48,cy),(cx+rx*.48,cy)])
    else:
        line([(cx-rx,cy-ry*.5),(cx,cy+ry*.5),(cx+rx,cy-ry*.5)])
        line([(cx,cy-ry),(cx,cy+ry)])
glyph=np.array(canvas.filter(ImageFilter.GaussianBlur(.7)),dtype=float)/255
for key,array in zip(('BaseColor','Normal','ORM'),bronze(h,w,glyph)):save('T_MeteorRuneBand_'+key,array)
(P/'textures.json').write_text(json.dumps({'normal_convention':'OpenGL; Unreal flip_green_channel=True',
 'core_size':[2048,2048],'bronze_size':[1024,1024],'rune_band_size':[512,2048],
 'rune_count_per_head':24,'heat_channels':{'R':'sparse active fissure mask','G':'spatial pulse phase','B':'all recessed fissures'},
 'source':'Deterministic authored PBR maps; no image lighting baked into material'},indent=2),encoding='utf-8')
print('METEOR_CORE_PBR_AUTHORED',flush=True)
