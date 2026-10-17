"""Sample the original rail's PBR maps for the new coated adapter material."""
import json,numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).parent
uv=json.loads((O/'rail_surface_uv.json').read_text())
src=O.parent/'M870Tactical20261015/Original/Source/textures'
R={'samples':len(uv),'source':'M870 factory rail crown UV samples'}
for key in ('Albedo','Metalic','Roughness'):
    im=Image.open(src/('M870_Tactical_'+key+'.png')).convert('RGB')
    a=np.array([im.getpixel((min(im.width-1,int(u*im.width)),min(im.height-1,int((1-v)*im.height)))) for u,v in uv],float)/255
    value=np.median(a,axis=0);R[key]=value.tolist()
    if key=='Albedo':R['base_color_linear']=np.where(value<=.04045,value/12.92,((value+.055)/1.055)**2.4).tolist()
(O/'finish.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M870_ADAPTER_FINISH_AUTHORED',flush=True)
