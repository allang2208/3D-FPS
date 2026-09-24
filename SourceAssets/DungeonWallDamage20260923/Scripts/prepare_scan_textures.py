"""Quilt aligned PBR channels from clean exposed aggregate regions of the acquired scan."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('D:/FPS3D/VaultCache/FabLibrary/Angled_Concrete_Wall_Section_with_Heavy_Damage-0b06ec58/fbx')
SOURCE=CACHE/'fmp_mbl_exp_cws05_fbx_v0_extracted/FMP_MBL_EXP_CWS05_FBX_v01/Textures/8K'
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
# Normalized IMAGE coordinates, not UV coordinates; avoid padded atlas islands and paint.
CROPS=[(1003,(.340,.754,.460,.874)),(1001,(.010,.714,.130,.834))]
channels=('BaseColor','Normal','ORM');sources=[];provenance=[]
for udim,box in CROPS:
    values=[]
    for channel in channels:
        path=SOURCE/f'T_FMP_MBL_EXP_CWS05_v01_{channel}_8K_UDIM.{udim}.png'
        with Image.open(path) as img:
            rect=tuple(int(v*img.size[i%2]) for i,v in enumerate(box))
            data=np.array(img.crop(rect).convert('RGB'),dtype=np.float32)/255
        values.append(data)
        provenance.append(dict(file=str(path),crop=box,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    sources.append(np.concatenate(values,axis=2))
rng=np.random.default_rng(923611);size=1024;patch=256;overlap=48;step=patch-overlap
canvas=np.zeros((size,size,9),np.float32);written=np.zeros((size,size),bool)
def cut_vertical(error):
    # Minimum error boundary, shared by albedo, normal, AO, roughness and metal.
    h,w=error.shape;cost=error.copy();prev=np.zeros((h,w),np.int16)
    for y in range(1,h):
        padded=np.pad(cost[y-1],(1,1),constant_values=1e20)
        choices=np.stack([padded[:w],padded[1:w+1],padded[2:w+2]])
        k=np.argmin(choices,axis=0);cost[y]+=choices[k,np.arange(w)]
        prev[y]=np.clip(np.arange(w)+k-1,0,w-1)
    line=np.empty(h,int);line[-1]=np.argmin(cost[-1])
    for y in range(h-1,0,-1):line[y-1]=prev[y,line[y]]
    return np.arange(w)[None,:]<=line[:,None]
for y in range(0,size,step):
    for x in range(0,size,step):
        h=min(patch,size-y);w=min(patch,size-x);old=canvas[y:y+h,x:x+w];mask=written[y:y+h,x:x+w]
        choices=[]
        for k in range(36):
            src=sources[int(rng.integers(len(sources)))];sy=int(rng.integers(0,src.shape[0]-h+1));sx=int(rng.integers(0,src.shape[1]-w+1))
            candidate=src[sy:sy+h,sx:sx+w]
            error=((old[:,:,:3]-candidate[:,:,:3])**2).mean(axis=2)+.15*(old[:,:,7]-candidate[:,:,7])**2
            choices.append((float(error[mask].mean()) if mask.any() else 0,candidate,error))
        score,candidate,error=min(choices,key=lambda q:q[0]);keep=np.zeros((h,w),bool)
        if x:keep[:,:overlap]=cut_vertical(error[:,:overlap])
        if y:keep[:overlap,:]|=cut_vertical(error[:overlap,:].T).T
        canvas[y:y+h,x:x+w]=np.where(keep[:,:,None],old,candidate);written[y:y+h,x:x+w]=True
# A narrow symmetric seam blend makes the scanned quilt periodic without changing UV islands.
for axis in (0,1):
    for i in range(20):
        a=[slice(None)]*3;b=a.copy();a[axis]=i;b[axis]=size-1-i
        a=tuple(a);b=tuple(b);mean=(canvas[a]+canvas[b])*.5;weight=(1-i/20)**2
        va=canvas[a].copy();vb=canvas[b].copy();canvas[a]=va*(1-weight)+mean*weight;canvas[b]=vb*(1-weight)+mean*weight
normal=canvas[:,:,3:6]*2-1;normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-5)
canvas[:,:,3:6]=normal*.5+.5
files={}
for index,channel in enumerate(channels):
    path=OUT/f'FabExposedConcrete_{channel}.png'
    Image.fromarray(np.uint8(np.clip(canvas[:,:,index*3:index*3+3]*255,0,255))).save(path)
    files[channel]=str(path)
meta=json.loads((CACHE/'metadata').read_text(encoding='utf-16'))
record=dict(title=meta['listing']['title'],listing_id=meta['listing']['uid'],
    url='https://www.fab.com/listings/'+meta['listing']['uid'],provider='MICROBACKLOT',
    acquisition='existing user-acquired Fab cache; user requested reuse; no purchase',
    cache=str(CACHE),source_textures=provenance,channels=files,resolution=1024,
    normal_green_flip=bool(meta.get('invertedNormal',False)),orm='R=AO G=roughness B=metallic',
    modifications='aligned multi-channel min-cut quilting of exposed aggregate only; periodic seam blend; original normal preserved',
    redistribution='local game use; do not publish source scans or derived textures as a standalone asset',runtime_tested=False)
(ROOT/'Sources/provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('FAB_CONCRETE_TEXTURES_AUTHORED',len(files),flush=True)
