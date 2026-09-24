"""Author seamless iron/gold micro-surface data and tangent normals; no preview rendering."""
import bpy, numpy as np
from pathlib import Path
OUT=Path(__file__).parent/'Textures';OUT.mkdir(exist_ok=True)
N=1024;rng=np.random.default_rng(92223)
def noise(scale):
    data=rng.normal(size=(N,N))
    fy=np.fft.fftfreq(N)[:,None];fx=np.fft.fftfreq(N)[None,:]
    data=np.fft.ifft2(np.fft.fft2(data)*np.exp(-(fx*fx+fy*fy)*scale*scale)).real
    return np.clip((data-data.mean())/(data.std()*5)+.5,0,1)
def write(name,rgb):
    pixels=np.concatenate([rgb,np.ones((N,N,1))],axis=2).astype(np.float32)
    image=bpy.data.images.new(name,width=N,height=N,alpha=True)
    image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG';image.save()
for family in ('Iron','Gold'):
    broad=noise(90);grain=noise(3);pits=noise(10)
    scratches=np.zeros((N,N))
    for _ in range(350):
        x=int(rng.integers(N));y=int(rng.integers(N));length=int(rng.integers(4,90));slope=rng.uniform(-.25,.25)
        for step in range(length):
            scratches[(y+step)%N,(x+int(step*slope))%N]=rng.uniform(.3,.9)
    height=(grain*.22+pits*.45-scratches*.15) if family=='Iron' else grain*.09+pits*.09-scratches*.13
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.45
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.45
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=2)
    normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rough=np.clip(grain*.35+broad*.55+scratches*.3,0,1)
    write('T_Treasure_'+family+'_Surface',np.stack((broad,grain,rough),axis=2))
    write('T_Treasure_'+family+'_Normal',normal*.5+.5)
print('TREASURE_SURFACE_MAPS_WRITTEN '+str(OUT))
