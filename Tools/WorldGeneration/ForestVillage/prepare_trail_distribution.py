"""Pack distant grass cover and two metric road-distortion fields in one linear atlas."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates

def prepare(source):
    yy,xx=np.mgrid[:512,:512]
    def field(seed,spacing):
        rng=np.random.default_rng(seed)
        lattice=rng.uniform(-1.,1.,(int(1024/spacing)+6,)*2)
        return map_coordinates(lattice,[yy*2./spacing+2,xx*2./spacing+2],order=3,mode='nearest')
    grass=source/'Grass'
    counts=np.fromfile(grass/'far_coverage.u32','<u4').reshape(512,512)
    density=gaussian_filter(counts.astype('f4'),1.0)
    turf=np.clip(density/1.20,0,1)
    soil=np.fromfile(source/'paint.rg8','u1').reshape(1025,1025,2)[1::2,1::2,0]/255.
    wet=np.fromfile(grass/'pond_shore.u8','u1').reshape(1025,1025)[1::2,1::2]/255.
    turf*=np.clip(1.-soil*1.6,0,1)*(1.-wet)
    # Fade coordinate distortion into the shared Landscape, village gate and quarry apron.
    x,y=-623.+xx*2.,-319.+yy*2.
    distance=np.hypot(np.maximum(abs(x)-252.,0.),np.maximum(abs(y)-252.,0.))
    gate=np.hypot(x-89.,y-327.)
    yard=np.hypot(x+425.,y-290.)
    feather=np.clip(np.minimum.reduce((distance,gate,yard))/12.,0,1)
    feather*=feather*(3.-2.*feather)
    phases=[.5+feather*(.33*field(s,22.)+.12*field(s+3,7.5)) for s in (12735,55304)]
    atlas=np.stack([turf,*phases],axis=2)
    Image.fromarray(np.rint(atlas.clip(0,1)*255.).astype('u1')).save(grass/'T_HillsTrailField.png')

if __name__=='__main__':prepare(Path(sys.argv[1]))
