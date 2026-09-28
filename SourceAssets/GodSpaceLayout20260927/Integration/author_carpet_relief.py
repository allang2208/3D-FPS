"""Reconstruct periodic pile relief from the existing normal data, not albedo.

The result is an approximate integrable height field, not a measured scan.
Its physical-height normal and occlusion stay registered with that height.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).parent
OUT=ROOT/'CarpetRelief';OUT.mkdir(exist_ok=True)
SIZE=2048
TILE_CM=90.0
DEPTH_CM=.38
source=ROOT/'CarpetSources/T_Carpet_01_N.tga'
n=np.asarray(Image.open(source).convert('RGB').resize((SIZE,SIZE),Image.Resampling.LANCZOS),dtype=np.float32)/127.5-1
n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),.001)
# Periodic least-squares integration of dH/du,dH/dv. Zero DC removes the
# source's mean tangent bias. The slope field uses the same +V convention
# as the material's world XY projection and UE's decoded source normal.
p=-n[:,:,0]/np.maximum(n[:,:,2],.3)
q=-n[:,:,1]/np.maximum(n[:,:,2],.3)
p-=p.mean();q-=q.mean()
kx=(2*np.pi*np.fft.rfftfreq(SIZE))[None,:]
ky=(2*np.pi*np.fft.fftfreq(SIZE))[:,None]
denom=kx*kx+ky*ky
hfft=(-1j*kx*np.fft.rfft2(p)-1j*ky*np.fft.rfft2(q))/np.maximum(denom,1e-12)
# Eliminate non-integrable scan drift and broad shading-scale slopes while
# retaining tufts and strands. No height is taken from the black colour map.
highpass=1-np.exp(-denom*42**2*.5)
lowpass=np.exp(-denom*.7**2*.5)
h=np.fft.irfft2(hfft*highpass*lowpass,s=(SIZE,SIZE)).astype(np.float32)
lo,hi=np.percentile(h,[.25,99.75])
h=np.clip((h-lo)/(hi-lo),0,1)
dx=(np.roll(h,-1,1)-np.roll(h,1,1))*DEPTH_CM/(2*TILE_CM/SIZE)
dy=(np.roll(h,-1,0)-np.roll(h,1,0))*DEPTH_CM/(2*TILE_CM/SIZE)
hn=np.stack((-dx,-dy,np.ones_like(h)),axis=2)
hn/=np.linalg.norm(hn,axis=2,keepdims=True)
packed=np.stack((h,.74+.26*np.sqrt(h),.77+.13*(1-h)),axis=2)
Image.fromarray(np.uint8(np.clip(hn*.5+.5,0,1)*255+.5),'RGB').save(OUT/'T_GodSpaceCarpetRelief_N.png')
Image.fromarray(np.uint8(packed*255+.5),'RGB').save(OUT/'T_GodSpaceCarpetRelief_HAR.png')
report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'method':'Periodic least-squares normal integration with bounded bandpass; not albedo-derived',
    'height_is_reconstructed_approximation':True,'size':SIZE,'tile_cm':TILE_CM,'depth_cm':DEPTH_CM,
    'channels':{'HAR':'R height, G local cavity approximation, B roughness'},'files':{}}
for path in OUT.glob('*.png'):report['files'][path.stem]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
