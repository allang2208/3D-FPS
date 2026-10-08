"""Recolor only original metal-mask regions; preserve jade, wrapping and silk."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P=Path(__file__).resolve().parent
S=P.parent/'ModelV1/Textures';D=P/'Textures'
src=np.asarray(Image.open(S/'Image_0.jpg').convert('RGB'),dtype=np.float32)/255
orm=np.asarray(Image.open(S/'Image_1.jpg').convert('RGB'),dtype=np.float32)/255
metal=np.clip((orm[:,:,2]-.28)/.36,0,1)
lum=src@np.array([.2126,.7152,.0722])
detail=lum-gaussian_filter(lum,7)
palette=np.array([222,157,109],dtype=np.float32)/255
copper=palette[None,None,:]*(1+np.clip(detail,-.16,.16)[...,None]*.75)
color=src*(1-metal[...,None])+copper*metal[...,None]
orm[:,:,1]=orm[:,:,1]*(1-metal)+np.clip(.31-detail*.08,.25,.39)*metal
orm[:,:,2]=orm[:,:,2]*(1-metal)+.97*metal
maps=[('BaseColor',color),('ORM',orm)]
if '--finish-only' not in sys.argv:
    maps.append(('Normal',np.asarray(Image.open(S/'Image_2.jpg').convert('RGB'),dtype=np.float32)/255))
for name,a in maps:
    Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(D/('Hilt_'+name+'.png'))
recipe_path=P/'surface_recipe.json'
recipe=json.loads(recipe_path.read_text(encoding='utf-8-sig'))
recipe['hilt_finish']={'name':'bright copper','srgb_palette_255':[222,157,109],
    'roughness_base':.31,'metallic':.97,'mask':'Original Image_1.jpg metallic channel',
    'scope':'Guard, pommel ring and shared metal fittings; nonmetal jade, wrapping and silk retain their source colors',
    'normal':'Existing Hilt_Normal.png unchanged during finish-only updates'}
recipe['steel']['scope']='Legacy V2 blade only; current blade uses BladeV3/surface_recipe.json'
recipe_path.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_COPPER_HILT_MAPS_SAVED',flush=True)
