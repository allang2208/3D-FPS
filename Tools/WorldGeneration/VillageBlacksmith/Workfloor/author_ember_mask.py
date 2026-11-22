"""Bake the bed's fissures and hot underside from the same coal centres used for modelling."""
import random
from pathlib import Path
import numpy as np
from PIL import Image
from coal_layout import grate_coals


def bake(path):
    resolution = 512
    x,y = np.meshgrid(-40+(np.arange(resolution)+.5)*80/resolution,
                      -38+(np.arange(resolution)+.5)*64/resolution)
    # Warp the seam edge on two scales so the cracks follow chipped coal instead of straight bisectors.
    qx=x+.74*np.sin(.47*y+.19*x)+.22*np.sin(2.1*y-.3*x)
    qy=y+.66*np.sin(.39*x-.16*y)+.29*np.sin(1.13*x+.80*y)
    cells=list(grate_coals(random.Random(8102)))
    dst=np.stack([np.hypot((qx-cx)/a,(qy-cy)/b) for _,cx,cy,_,a,b,_ in cells])
    nearest=np.partition(dst,1,axis=0)
    gap=nearest[1]-nearest[0]
    # Fuel is hottest around the fire's centre. The outer handfuls keep a dark crust.
    field=np.exp(-((x-1)/26)**2-((y+6)/18)**2)
    bands=.75+.25*np.sin(.36*x+.25*y+np.sin(.61*y))
    heat=np.clip(field*bands*1.35,0,1)
    broad=heat*np.exp(-(gap/.46)**2)
    core=heat**2*np.exp(-(gap/.15)**2)
    side=heat*np.clip(nearest[0],0,1)**2
    pixels=np.rint(255*np.clip(np.stack([broad,core,side],axis=-1),0,1)).astype(np.uint8)
    Image.fromarray(pixels).save(path)


if __name__=='__main__':
    output=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageBlacksmith20261117/Workfloor'
    bake(output/'T_SmithEmberBed_Heat.png')
