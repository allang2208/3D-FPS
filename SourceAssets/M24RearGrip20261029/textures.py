"""Physical-scale molded grip patterns, OpenGL tangent normals for UE green-flip import."""
import numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).resolve().parent/'Textures';O.mkdir(exist_ok=True)
N=1024;y,x=np.mgrid[:N,:N]/N
def normal(h):
    dy,dx=np.gradient(h,.08/N);v=np.stack((-dx,-dy,np.ones_like(h)),axis=-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
    return np.uint8(np.clip((v*.5+.5)*255,0,255))
# All heights are in metres; relief lives in the material, not hand-contact geometry.
noise=np.random.default_rng(24).random((N,N));micro=(np.sin(x*2*np.pi*193)*np.sin(y*2*np.pi*181))*.000004
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
    if key=='phantom_reargrip':
        # Interrupted ladder ribs and a narrow molded perimeter language.
        ribs=np.maximum(0,np.cos(x*2*np.pi*18))**5
        bands=.28+.72*(.5+.5*np.cos(y*2*np.pi*4))**6
        h=.000045*ribs*bands+micro
    elif key=='stable_antislip_reargrip':
        a=(x*47)%1-.5;b=(y*47+((x*47).astype(int)%2)*.5)%1-.5
        h=.000038*np.maximum(0,1-(a*a+b*b)*5)**2+micro+(noise-.5)*.000002
    else:
        h=.000028*np.maximum(0,np.cos(x*2*np.pi*28))**4+micro
    Image.fromarray(normal(h)).save(O/('T_M24_'+key+'_N.png'))
Image.new('RGBA',(4,4),(0,0,255,255)).save(O/'T_M24_GripSurfaceMask.png')
print('M24_REAR_GRIP_TEXTURES_CREATED')
