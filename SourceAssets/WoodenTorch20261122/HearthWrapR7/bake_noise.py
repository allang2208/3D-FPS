"""Bake a tileable three-dimensional turbulence field, with guard texels around every Z slice."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image

rng = np.random.default_rng(17603)
shape = (64,62,62)
def octave(s):
    f=gaussian_filter(rng.standard_normal(shape),s,mode="wrap")
    return (f-f.mean())/f.std()
channels=[.75*octave(4.1)+.28*octave(1.95)+.105*octave(.90),
          .72*octave(3.2)+.31*octave(1.5)+.15*octave(.76),
          .85*octave(5.2)+.25*octave(2.1)]
volume=np.stack(channels,axis=-1)
volume=np.round(np.clip(.5+.207*volume,0,1)*255).astype(np.uint8)
atlas=np.empty((512,512,3),dtype=np.uint8)
for z,slice_ in enumerate(volume):
    y,x=divmod(z,8)
    atlas[y*64:y*64+64,x*64:x*64+64]=np.pad(slice_,((1,1),(1,1),(0,0)),mode="wrap")
Image.fromarray(atlas).save(Path(__file__).resolve().parent/"Export/T_HearthFlowVolume.png")
