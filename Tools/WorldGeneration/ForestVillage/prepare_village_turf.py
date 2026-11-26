"""Build the village grass PBR inputs and its protected one-metre ground relief."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates
from generate_village_relief import generate

def prepare(src):
    raw=src/'Fab/2f4c8d27-9de0-43c4-ae85-1038b4eda16a'
    out=src/'Turf';out.mkdir(exist_ok=True)
    def channel(s):return Image.open(next(raw.glob('*_2K_'+s+'.jpg')))
    channel('BaseColor').save(out/'T_VillageGrass_B.png')
    channel('Normal').save(out/'T_VillageGrass_N.png')
    height=channel('Displacement').convert('L')
    Image.merge('RGB',(channel('AO').convert('L'),channel('Roughness').convert('L'),height)).save(out/'T_VillageGrass_ARH.png')
    setback,open_ground=generate(src.parent/'VillageGroundRelief-R11',site_weights=True)
    # Condense the same measured displacement into shallow turf hummocks resolvable on the metre grid.
    h=gaussian_filter(np.asarray(height.resize((96,96),Image.Resampling.BOX),dtype=float)/255.,4.,mode='wrap')
    h=(h-h.mean())/max(h.std(),.001)
    y,x=np.indices(setback.shape)
    sample=map_coordinates(h,[2.7*y+.45*x,3.3*x-.37*y],order=1,mode='grid-wrap')
    rim=np.minimum.reduce((x,118-x,y,145-y))
    weight=setback*open_ground*np.clip((rim-1.)/4.,0.,1.)
    # Keep the highest-frequency geometry out of walking collision. It is represented by shader parallax.
    delta=np.rint(4.*np.tanh(sample)*weight).astype('<i2')
    original=np.fromfile(src.parent/'ReferenceHill-R12/settlement.i16','<i2').reshape(delta.shape)
    (original+delta).astype('<i2').tofile(out/'settlement.i16')
    (out/'relief.json').write_text(json.dumps(dict(changed=int(np.count_nonzero(delta)),min_cm=int(delta.min()),max_cm=int(delta.max()))))
if __name__=='__main__':prepare(Path(sys.argv[1]))
