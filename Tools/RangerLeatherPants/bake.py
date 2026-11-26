"""Physical 8 cm leather / twill fields for the approved trouser concept."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerLeatherPants20261021';T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
N=2048;SPAN=8.;rng=np.random.default_rng(2026102102);v,u=np.mgrid[:N,:N].astype(np.float32)/N
def noise(s):
    a=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),s,mode='wrap');return np.clip(a/max(float(a.std()),1e-8),-3,3)/3
def png(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(T/(name+'.png'))
def output(name,h,base,rough,ao):
    h=gaussian_filter(h,.65,mode='wrap');dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*SPAN/N);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*SPAN/N)
    normal=np.stack((-dx,dy,np.ones_like(h)),-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    png(name+'_BaseColor',base);png(name+'_Normal',normal*.5+.5);png(name+'_ORM',np.stack((ao,rough,np.zeros_like(h)),-1))
    # FBX has no portable channel-extraction graph for packed ORM. Provide a
    # derived scalar image for interchange while the authored PBR keeps ORM.
    (T/'Exchange').mkdir(exist_ok=True);Image.fromarray(np.uint8(np.clip(rough,0,1)*255+.5)).save(T/'Exchange'/(name+'_Roughness.png'))
    np.save(T/(name+'_height_cm.npy'),h.astype(np.float32))
grid=88;yy,xx=np.mgrid[:grid,:grid];sites=np.stack(((xx+rng.uniform(.12,.88,(grid,grid)))/grid,(yy+rng.uniform(.12,.88,(grid,grid)))/grid),-1).reshape(-1,2)
tree=cKDTree(sites,boxsize=1.);ridge=np.empty((N,N),np.float32)
for y in range(0,N,64):
    ds,_=tree.query(np.stack((u[y:y+64],v[y:y+64]),-1).reshape(-1,2),k=2,workers=4);ridge[y:y+64]=(ds[:,1]-ds[:,0]).reshape(-1,N)*grid
grain=gaussian_filter(np.tanh(ridge*5.5),.85,mode='wrap');broad=noise(90);mottle=noise(18);fine=noise(1.6);pores=np.maximum(-noise(1.2)-.35,0)**2
h=.0054*grain+.0003*mottle+.00012*fine-.0018*pores
output('WalnutLeather',h,np.array([.295,.176,.092])*(1+.045*broad+.025*mottle+.035*grain)[...,None],np.clip(.63+.045*broad+.02*mottle-.035*grain,.48,.74),np.clip(.97+.03*grain-.03*pores,.90,1))
output('ReinforcedLeather',h*.82,np.array([.210,.115,.054])*(1+.04*broad+.025*mottle+.025*grain)[...,None],np.clip(.59+.04*broad-.025*grain,.46,.71),np.clip(.97+.03*grain-.03*pores,.9,1))
threads=168;warp=u*threads;weft=v*threads;cross=gaussian_filter((((np.floor(warp)+np.floor(weft))%4)<2).astype(np.float32),N/threads*.13,mode='wrap')
a=(.5-.5*np.cos(math.tau*warp))**2;b=(.5-.5*np.cos(math.tau*weft))**2;slub=noise(26);dye=noise(90)
ha=.0032*a*(.4+.6*cross);hb=.0032*b*(1-.6*cross);h=.5*(ha+hb+np.sqrt((ha-hb)**2+.00009**2))+.00015*noise(1.2)+.00016*slub
output('OliveTwill',h,np.array([.180,.196,.119])*(1+.04*dye+.022*slub)[...,None],np.clip(.86+.025*slub-.012*(a+b),.77,.93),.96+.04*np.maximum(a,b))
(R/'surfaces.json').write_text(json.dumps(dict(completed=True,tile_cm=8,texture_size=N,normal_convention='OpenGL (-dH/du,+dH/draster_row,+1), Blender UV=(u,1-v); UE flip green once',orm='R AO, G roughness, B metalness',physical_height_fields=True,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.png')},families=['WalnutLeather','ReinforcedLeather','OliveTwill']),indent=2),encoding='utf-8')
print('RANGER_TROUSER_PBR_AUTHORED',flush=True)
