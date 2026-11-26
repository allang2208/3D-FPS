"""Band-limited 8 cm leather/cotton relief with an explicit raster-to-tangent basis."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FieldRangerTop20261020/TailoredFinish20261021');T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
N=2048;SPAN=8.;rng=np.random.default_rng(20261021)
v,u=np.mgrid[:N,:N].astype(np.float32)/N
def noise(sigma):
    field=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),sigma,mode='wrap')
    return np.clip(field/max(float(field.std()),1e-8),-2.8,2.8)/2.8
def png(name,data):Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(T/(name+'.png'))
def output(name,h,color,rough,ao):
    # Filter the physical height before differentiating; do not blur RGB normals.
    h=gaussian_filter(h,.55,mode='wrap').astype(np.float32)
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*SPAN/N);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*SPAN/N)
    # PNG rows increase downwards, while Blender exports garment UV as (u,1-v).
    # OpenGL tangent +Y therefore corresponds to NEGATIVE raster-row direction.
    # UE's one green-channel flip then gives the engine's DirectX tangent basis.
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    png(name+'_BaseColor',color);png(name+'_Normal',normal*.5+.5)
    png(name+'_ORM',np.stack((np.clip(ao,.88,1),np.clip(rough,.42,.94),np.zeros_like(h)),-1))
    np.save(T/(name+'_height_cm.npy'),h.astype(np.float32))

# Periodic jittered cells have no preferred direction, unlike the old sine bands.
grid=128;yy,xx=np.mgrid[:grid,:grid];sites=np.stack(((xx+rng.uniform(.15,.85,(grid,grid)))/grid,(yy+rng.uniform(.15,.85,(grid,grid)))/grid),-1).reshape(-1,2)
tree=cKDTree(sites,boxsize=1.0);ridge=np.empty((N,N),np.float32)
for start in range(0,N,64):
    query=np.stack((u[start:start+64],v[start:start+64]),-1).reshape(-1,2);distance,_=tree.query(query,k=2,workers=4)
    ridge[start:start+64]=(distance[:,1]-distance[:,0]).reshape(-1,N)*grid
grain=np.tanh(ridge*6);grain=gaussian_filter(grain,1.0,mode='wrap');fine=noise(1.6);broad=noise(72);mottle=noise(18)
pores=np.clip(-noise(1.1)-.33,0,1)**2
height=.00165*grain+.00020*fine-.0009*pores+.00025*mottle
color=np.array([.245,.159,.100],np.float32)*(1+.075*broad+.035*mottle+.015*grain)[...,None]
output('RangerLeather',height,color,.64+.045*broad+.028*mottle-.018*grain,1-.035*(1-grain)-.020*pores)

# Individual flattened yarns with a real 2/2 crossing pattern and subtle slubs.
threads=176;warp_phase=u*threads;weft_phase=v*threads
crossing=(((np.floor(warp_phase)+np.floor(weft_phase))%4)<2).astype(np.float32)
crossing=gaussian_filter(crossing,N/threads*.15,mode='wrap')
# Yarn peaks sit at cell centers; the over/under field changes smoothly between them.
warp=(.5-.5*np.cos(math.tau*warp_phase))**2;weft=(.5-.5*np.cos(math.tau*weft_phase))**2
slub=noise(22);fibers=noise(1.15);dye=noise(80)
warp_h=.0026*warp*(.38+.62*crossing);weft_h=.0026*weft*(1-.62*crossing)
height=.5*(warp_h+weft_h+np.sqrt((warp_h-weft_h)**2+.00009**2))+.00014*fibers+.00022*slub
color=np.array([.276,.300,.216],np.float32)*(1+.035*dye+.020*slub+.012*(warp-weft))[...,None]
output('RangerTwill',height,color,.85+.022*slub-.012*(warp+weft),.96+.04*np.maximum(warp,weft))
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.png')}
(R/'surfaces.json').write_text(json.dumps(dict(completed=True,revision='SurfaceNormals20261021',tile_cm=SPAN,texture_size=N,normal_convention='OpenGL (-dH/du,+dH/draster_row,+1); UE flips green once',height_axes='PNG rows +V down; Blender garment UV=(u,1-v)',physical_height_fields=True,filtered_height_before_derivative=True,continuous_twill_crossings=True,normal_strength=1.0,composite_normal_roughness_power=.7,leather_grain_pitch_mm=SPAN/grid*10,cotton_yarn_pitch_mm=SPAN/threads*10,materials=['RangerTwill','RangerLeather'],files=files,runtime_tested=False),indent=2),encoding='utf-8')
print('TAILORED_PBR_BAKED',len(files),flush=True)
