"""Sample the registered alpha and height of the one-metre Quixel scan."""
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
source=ROOT.parent/'FacilityQuixel20261108/Sources/DamagedConcrete'
n=113
color=Image.open(next(source.rglob('*B-O.png'))).convert('RGBA')
alpha=np.asarray(color.getchannel('A').resize((n,n),Image.Resampling.BOX))/255.
height_img=Image.open(next(source.rglob('*_H.png')))
height=np.asarray(height_img.resize((n,n),Image.Resampling.BOX)).astype(float)
if height.ndim==3:height=height[:,:,0]
lo,hi=np.percentile(height[alpha>.55],[5,95])
# Broad relief comes from the scan; its registered normal supplies the finer detail.
# Fade onto the original wall at broken edges. The wall itself stays at depth zero.
depth_cm=.02+.96*np.clip((height-lo)/(hi-lo),0,1)*np.clip((alpha-.18)/.78,0,1)
np.savez_compressed(ROOT/'relief-grid.npz',alpha=alpha,depth=depth_cm)
