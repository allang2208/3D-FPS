"""Read the retained native neck UVs into the M870-specific material recipe."""
import json,numpy as np
from pathlib import Path
from PIL import Image
O=Path(__file__).parent;S=O.parent.parent
uv=json.loads((O/'native_contact_uv.json').read_text())
R={'source':'M870 original stock grip/contact surface UV0','samples':len(uv)}
for key in ('Albedo','Roughness','Metalic'):
    im=Image.open(S/'M870Tactical20261015/Original/Source/textures'/('M870_Tactical_'+key+'.png')).convert('RGB')
    colors=np.array([im.getpixel((min(im.width-1,max(0,int(u*im.width))),min(im.height-1,max(0,int((1-v)*im.height))))) for u,v in uv],float)/255
    value=np.median(colors,axis=0);R[key]=value.tolist()
    if key=='Albedo':R['base_color_linear']=np.where(value<=.04045,value/12.92,((value+.055)/1.055)**2.4).tolist()
(O/'finish.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M870_NECK_FINISH',R)
