"""Author shared physically separated surface channels and age existing original print artwork."""
from pathlib import Path
import json,math,random
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'TransitIncidentDressing20261010'
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(101017);pr=random.Random(101017)
S=1024
yy,xx=np.mgrid[0:S,0:S].astype(np.float32);u=xx/S;v=yy/S

def noise_grid(cells):
    a=rng.random((cells,cells)).astype(np.float32)
    # Periodic bicubic lattice used only while authoring, never as runtime shader noise.
    tile=np.tile(a,(3,3))
    return np.array(Image.fromarray(tile).resize((S*3,S*3),Image.Resampling.BICUBIC),dtype=np.float32)[S:S*2,S:S*2]

def normal(height,strength):
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    a=np.stack((-dx,dy,np.ones_like(dx)),2);a/=np.linalg.norm(a,axis=2,keepdims=True)
    return np.uint8(np.clip(a*.5+.5,0,1)*255)

def byte(a):return np.uint8(np.clip(a,0,1)*255)
bc=np.zeros((S*2,S*2,3),dtype=np.uint8);nm=bc.copy();orm=bc.copy()
for idx,key in enumerate(('Plastic','Steel','Rubber','Cotton')):
    coarse=noise_grid(10);medium=noise_grid(47);grain=rng.random((S,S)).astype(np.float32)
    scratch=Image.new('L',(S,S));d=ImageDraw.Draw(scratch)
    for j in range(220 if key=='Steel' else 70):
        x=pr.randrange(S);y=pr.randrange(S);length=pr.randrange(4,70)
        dx=length if key=='Steel' else pr.randrange(-length,length+1)
        dy=pr.randrange(-2,3) if key=='Steel' else pr.randrange(4,length+1)
        d.line((x,y,x+dx,y+dy),fill=pr.randrange(50,220),width=1)
    scratches=np.array(scratch,dtype=np.float32)/255
    if key=='Plastic':
        # Neutral tintable substrate: polish smears and shallow contact scratches.
        tone=.79+.12*coarse+.04*medium+scratches*.035
        color=np.repeat(tone[:,:,None],3,2);height=grain*.05+medium*.025-scratches*.07
        rough=.45+.15*coarse-.12*scratches;metal=0.;ao=np.ones_like(rough)
    elif key=='Steel':
        brushed=rng.random((S,1)).astype(np.float32)*.08
        tone=.52+.11*coarse+brushed+scratches*.09
        color=np.stack((tone*.95,tone*.98,tone),2)
        height=brushed*.3-scratches*.035;rough=.31+.18*medium+scratches*.13;metal=1.;ao=np.ones_like(rough)
    elif key=='Rubber':
        tone=.19+.09*coarse+.025*medium
        color=np.stack((tone*.90,tone*.96,tone),2)
        height=(grain>.80)*.045+medium*.08;rough=.76+.13*medium;metal=0.;ao=.96+.04*grain
    else:
        strand=(.5+.5*np.cos((u*112+v*29)*math.tau))**4
        fine=(.5+.5*np.cos((u*448+v*116)*math.tau))**3
        tone=.66+.13*coarse+.09*strand+.035*fine
        color=np.stack((tone,tone*.965,tone*.86),2)
        height=strand*.12+fine*.025+grain*.018;rough=.85+.12*medium;metal=0.;ao=.86+.14*strand
    i=idx%2;j=idx//2;sl=(slice(j*S,(j+1)*S),slice(i*S,(i+1)*S))
    bc[sl]=byte(color);nm[sl]=normal(height,1.6);orm[sl]=byte(np.stack((ao,np.clip(rough,.1,.99),np.full_like(rough,metal)),2))
for key,arr in (('Surfaces_BC',bc),('Surfaces_NormalDX',nm),('Surfaces_ORM',orm)):
    Image.fromarray(arr).save(OUT/('T_IncidentDetail_'+key+'.png'))

# Preserve the original print layout; add fibre, crease wear, absorbed stains and handling marks.
source=np.array(Image.open(OLD/'Authored/Textures/T_Incident_Forms.png').convert('RGB'),dtype=np.float32)/255
height=np.zeros((2048,2048),dtype=np.float32);rough=np.zeros_like(height);ao=np.ones_like(height)
for idx in range(4):
    sl=(slice(idx//2*S,(idx//2+1)*S),slice(idx%2*S,(idx%2+1)*S))
    fine=rng.random((S,S)).astype(np.float32);mottle=noise_grid(14)
    edge=np.minimum.reduce((u,1-u,v,1-v));edge_dirt=np.exp(-edge*32)*(.10+.12*mottle)
    stain=np.zeros_like(u)
    for _ in range(4):
        cx,cy=pr.random(),pr.random();rx,ry=pr.uniform(.08,.28),pr.uniform(.09,.3)
        stain+=np.exp(-((u-cx)**2/rx**2+(v-cy)**2/ry**2)*2)*pr.uniform(.012,.065)
    # Interrupted boot sole scuff on two sheets, kept faint enough to retain the form.
    scuff=Image.new('L',(S,S));d=ImageDraw.Draw(scuff)
    if idx in (1,3):
        for row in range(9):
            for col in range(3):
                x=250+col*71+row*22;y=178+row*54
                d.rounded_rectangle((x,y,x+43,y+26),radius=4,fill=35+pr.randrange(30))
    sc=np.array(scuff.filter(ImageFilter.GaussianBlur(1.3)),dtype=np.float32)/255
    tint=np.stack((1-edge_dirt*.40-stain*.32-sc*.40,1-edge_dirt*.50-stain*.49-sc*.43,1-edge_dirt*.72-stain*.86-sc*.48),2)
    source[sl]*=tint;source[sl]+=((fine-.5)*.009)[:,:,None]
    crease=np.exp(-((u-(.50+.009*np.sin(v*5)))/.0035)**2)
    h=(fine-.5)*.014+crease*.033
    if idx==2:h+=np.exp(-((v-.58)/.004)**2)*.024
    height[sl]=h;rough[sl]=.91-fine*.045-stain*.35-sc*.09;ao[sl]=1-edge_dirt*.09
Image.fromarray(byte(source)).save(OUT/'T_IncidentDetail_Forms_BC.png')
Image.fromarray(normal(height,1.4)).save(OUT/'T_IncidentDetail_Forms_NormalDX.png')
Image.fromarray(byte(np.stack((ao,rough,np.zeros_like(rough)),2))).save(OUT/'T_IncidentDetail_Forms_ORM.png')

im=Image.open(OLD/'Authored/Textures/T_Incident_Caution.png').convert('RGB');arr=np.array(im,dtype=np.float32)/255
h,w=arr.shape[:2];wear=Image.new('L',(w,h));d=ImageDraw.Draw(wear)
for _ in range(150):
    x=pr.randrange(w);y=pr.randrange(h);l=pr.randrange(2,22);d.line((x,y,x+l,y+pr.randrange(-2,3)),fill=pr.randrange(60,140),width=1)
wx=np.array(wear,dtype=np.float32)/255
arr=arr*(1-wx[:,:,None]*.15)+np.array([.58,.46,.17])[None,None,:]*wx[:,:,None]*.18
Image.fromarray(byte(arr)).save(OUT/'T_IncidentDetail_Caution_BC.png')
(ROOT/'textures.json').write_text(json.dumps(dict(atlas_size=[2048,2048],surface_tiles=['Plastic','Steel','Rubber','Cotton'],
    packed_channels=dict(R='ambient occlusion',G='roughness',B='metallic'),normal='DirectX tangent space',
    artwork_source=str(OLD/'Authored/Textures'),files=[p.name for p in OUT.glob('*.png')]),indent=2),encoding='utf8')
print('INCIDENT_DETAIL_TEXTURES_WRITTEN')
