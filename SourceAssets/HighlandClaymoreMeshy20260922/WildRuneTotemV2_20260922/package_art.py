"""Copy the generated coverage image intact; derive the shader sampling window."""
import json,shutil
from pathlib import Path
from PIL import Image
import numpy as np
P=Path(__file__).resolve().parent
source=Path(r'C:\Users\allan\.codex\generated_images\01a0c6c5-5fe4-7550-8c0f-abed299812e8\exec-2adad4cd-48b9-47d1-b7ea-ad772cd1b27b.png')
(P/'Textures').mkdir(exist_ok=True)
dest=P/'Textures/T_WildTotem_Generated.png'
shutil.copy2(source,dest)
# Read the original pixels to choose projection coordinates. No crop, recolor,
# blur or other image edit is saved: the generated raster remains unchanged.
with Image.open(dest) as im:
    w,h=im.size;pixels=np.asarray(im.convert('RGB'))
yy,xx=np.where(pixels[:,:,0]>28)
margin=14
bounds=[max(0,int(xx.min())-margin),max(0,int(yy.min())-margin),
        min(w,int(xx.max())+margin+1),min(h,int(yy.max())+margin+1)]
x0,y0,x1,y1=bounds
production={'name':'蛮荒符文 · 兽颚破甲战纹 V2','weapon':'ue_highland_claymore','option':'wild_rune',
    'generated_source':str(source),'mask':str(dest),'generator':'Built-in imagegen','prompt':'imagegen_prompt.txt',
    'image_size':[w,h],'source_art_bounds_px':bounds,'art_uv_rect':[x0/w,y0/h,(x1-x0)/w,(y1-y0)/h],
    'raster_edits':False,'orientation':'generated spear left, beast jaw right; blade tip maps left and guard maps right',
    'design':'One continuous asymmetric composition: beast-jaw seal, distinct claw cuts, broken backbone and bone spear tip',
    'colors_linear':{'WildCoreColor':[.32,.006,.004,1],'WildGlowColor':[1,.022,.006,1]},
    'scalars':{'WildPulseSpeed':1.12,'EmissionPeak':1.8,'RuneOpacity':.88,'HaloOpacity':.145,'HaloRadiusTexels':1.8},
    'unchanged_stats':{'toughness_damage_mult':1.3,'physical_armor_penetration':.2},
    'tested':False}
(P/'production.json').write_text(json.dumps(production,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'image_size':[w,h],'art_bounds':bounds,'uv_rect':production['art_uv_rect']}))
