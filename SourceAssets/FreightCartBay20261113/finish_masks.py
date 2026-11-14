from pathlib import Path
from PIL import Image
import numpy as np
r=Path(__file__).resolve().parent
for kind in ('Platform','Wall'):
    name='T_'+kind+'PatinaColor.png'
    im=np.asarray(Image.open(r/name).convert('RGBA'),dtype=np.float32)/255.
    if kind=='Platform':
        m=np.asarray(Image.open(r/'T_CartBayFloorMasks.png').resize((2048,2048),Image.Resampling.BILINEAR),dtype=np.float32)/255.
        im[:,:,3]*=(1.-.41*m[:,:,0])*(1.-.16*m[:,:,1])
    else:
        donor=r.parent/'DungeonWallUpgrade20260924/Sources/PolyHaven/plastered_wall_diff_4k.jpg'
        surface=np.asarray(Image.open(donor).convert('L').resize((2048,2048),Image.Resampling.LANCZOS),dtype=np.float32)/255.
        # Scan breakup is on the attached plaster veil; the original wall still supplies most of its color response.
        centered=surface-np.median(surface)
        im[:,:,:3]=np.clip(im[:,:,:3]*(1+1.55*centered[:,:,None]),0,1)
        im[:,:,3]=np.minimum(.66,im[:,:,3]*(1.05+2.5*abs(centered)))
    Image.fromarray(np.uint8(np.clip(im,0,1)*255)).save(r/('T_'+kind+'FinishCoverage.png'))
