"""Produce the baked atlas border mask for bounded leather parallax."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
sys.path.insert(0,str(Path(__file__).resolve().parent))
import glove_family_detail as lib

def finish(family):
 for group in lib.FAMILIES[family]['groups']:
  path=lib.R/family/'Textures'/group/('T_'+family+'_'+group+'_Relief.png')
  if not path.exists():continue
  image=Image.open(path).convert('RGB');width,height=image.size
  mask=Image.new('L',(width,height));draw=ImageDraw.Draw(mask)
  for face in lib.read(lib.R/family/'Baked'/(group+'.json'))['uv']:
   draw.polygon([(u*width,v*height) for u,v in face],fill=255)
  distance=distance_transform_edt(np.asarray(mask)>0);pixels=np.asarray(image).copy()
  pixels[:,:,2]=np.round(np.clip((distance-3)/17,0,1)*255).astype(np.uint8)
  Image.fromarray(pixels).save(path)
  print('COMPANION_ATLAS_FINISHED',family,group,flush=True)

if __name__=='__main__':
 for family in sys.argv[1:] or ['Fingerless','Tactical']:finish(family)
