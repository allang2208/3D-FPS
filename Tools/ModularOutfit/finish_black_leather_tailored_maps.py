"""Build atlas-edge fade for bounded parallax, retaining baked relief/fuzz."""
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
import black_leather_tailored_surface as lib

for group in ('M4','Body'):
    path=lib.R/'Textures'/group/('T_BlackLeather_'+group+'_Relief.png')
    image=Image.open(path).convert('RGB');width,height=image.size
    mask=Image.new('L',(width,height));draw=ImageDraw.Draw(mask)
    data=lib.read(lib.R/'Baked'/(group+'.json'))
    for face in data['uv']:
        draw.polygon([(u*width,v*height) for u,v in face],fill=255)
    distance=distance_transform_edt(np.asarray(mask)>0)
    pixels=np.asarray(image).copy()
    # At full relief the shift is at most 8 texels. Fade starts 3 pixels
    # inside the island, reaching full displacement only after 20 pixels.
    pixels[:,:,2]=np.round(np.clip((distance-3)/17,0,1)*255).astype(np.uint8)
    Image.fromarray(pixels).save(path)
    print('RELIEF_ATLAS_FINISHED',group,width,height,flush=True)
