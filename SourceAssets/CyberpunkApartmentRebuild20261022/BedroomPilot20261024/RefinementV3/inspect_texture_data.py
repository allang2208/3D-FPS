from pathlib import Path
from PIL import Image
import numpy as np,json
R=Path(__file__).resolve().parent
rows=[]
for name in ('T_TextilePlain_N','T_TextileStriped_N','T_WoodVeneer_Oak_N','T_Carpet_01_N'):
    with Image.open(R/'Review/LibraryTextures'/(name+'.png')) as image:
        data=np.array(image.convert('RGB'),dtype=np.float32)/255
    rows.append(dict(texture=name,mean=data.mean(axis=(0,1)).tolist(),std=data.std(axis=(0,1)).tolist(),minimum=data.min(axis=(0,1)).tolist(),maximum=data.max(axis=(0,1)).tolist()))
    step=max(1,data.shape[0]//512);small=data.reshape(data.shape[0]//step,step,data.shape[1]//step,step,3).mean(axis=(1,3))
    Image.fromarray(np.round(small*255).astype(np.uint8)).save(R/'Review'/(name+'-data.png'))
(R/'Review/normal-source-statistics.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows))
