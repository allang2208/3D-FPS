"""Physically scaled subdued metal microfinish; no colored mottling or dirt."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parent;T=O/'Textures';T.mkdir(exist_ok=True)
N=1024;tile=.04;yy,xx=np.mgrid[:N,:N]/N;rng=np.random.default_rng(2402902)
f=np.fft.fftfreq(N);kernel=np.exp(-2*np.pi**2*.8**2*(f[:,None]**2+f[None,:]**2))
recipe={}
for name,amplitude,rough_amp in [('Metal',.00000018,.008),('Steel',.00000024,.012),('Interior',.00000008,.004)]:
    fine=np.fft.ifft2(np.fft.fft2(rng.normal(size=(N,N)))*kernel).real
    fine/=max(fine.std(),1e-6)
    # A fine directional machining trace. Its amplitude is sub-micron, not grit.
    lines=np.sin(2*np.pi*(yy*211+.16*np.sin(xx*2*np.pi*7)))
    h=(.7*lines+.3*fine)*amplitude
    du=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))/(2*tile/N)
    dv=(np.roll(h,1,axis=0)-np.roll(h,-1,axis=0))/(2*tile/N)
    n=np.stack((-du,-dv,np.ones_like(h)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip(n*.5+.5,0,1)*255)).save(T/f'T_M24_AAS_V2_{name}_N.png')
    rough=np.clip(.5+rough_amp*(.7*lines+.3*np.clip(fine,-2,2)),0,1)
    Image.fromarray(np.uint8(rough*255)).save(T/f'T_M24_AAS_V2_{name}_R.png')
    recipe[name]=dict(tile_cm=tile*100,height_amplitude_m=amplitude,roughness_deviation=rough_amp,
        normal=f'T_M24_AAS_V2_{name}_N',roughness=f'T_M24_AAS_V2_{name}_R')
(O/'texture_recipe.json').write_text(json.dumps(dict(complete=True,normal_convention='OpenGL +Y; flip green in UE once',
    materials=recipe,grain_in_shared_master=0,low_frequency_mottle=0,uniform_scratches=0),indent=2))
print('M24_DETAIL_V2_MICROFINISH_SAVED',flush=True)
