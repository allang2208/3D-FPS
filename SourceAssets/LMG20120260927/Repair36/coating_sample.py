import numpy as np,json
from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).parent;D=O.parent/'Detail35'
color=np.asarray(Image.open(D/'Textures/T_LMG201_D35_Receiver_BaseColor.png').convert('RGB'))/255.;orm=np.asarray(Image.open(D/'Textures/T_LMG201_D35_Receiver_ORM.png').convert('RGB'))/255.;mask=np.asarray(Image.open(D/'Textures/ReceiverPanelMask.png'))>.25*255
linear=np.where(color<=.04045,color/12.92,((color+.055)/1.055)**2.4)
r={'region':'current receiver planar-region UV mask, excluding extreme highlights/marks','base_linear_median':np.median(linear[mask],axis=0).tolist(),'base_srgb_median':np.median(color[mask],axis=0).tolist(),'roughness_median':float(np.median(orm[mask,1])),'metallic_median':float(np.median(orm[mask,2]))}
(O/'coating_sample.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
