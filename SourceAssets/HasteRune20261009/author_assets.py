"""Author original wind-glyph source, blade mask and shared grayscale menu icon."""
from pathlib import Path
import json, math
from PIL import Image, ImageDraw, ImageFilter
P=Path(__file__).resolve().parent
# Unequal wind strokes converge into a split spear point. Artwork stays inside
# the common blade mask's central sampling band (u .30-.70).
polygons=[
 [(510,250),(552,690),(530,1250),(514,1140),(488,704)],
 [(514,995),(602,1285),(569,1620),(527,1900),(549,1500),(533,1300)],
 [(488,1200),(427,1515),(440,1960),(478,2310),(455,1805),(461,1510)],
 [(527,1720),(614,1970),(593,2310),(548,2630),(569,2210),(555,2040)],
 [(487,1950),(393,2280),(410,2620),(474,3075),(435,2520),(439,2310)],
 [(530,2490),(606,2750),(570,3150),(513,3580),(542,3060),(548,2825)],
 [(488,2840),(446,3130),(470,3470),(507,3780),(490,3370),(477,3170)],
 [(586,880),(650,1140),(618,1450),(622,1170)],
 [(427,2640),(367,2900),(401,3220),(395,2940)],
]
svg='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="4096" viewBox="0 0 1024 4096"><rect width="1024" height="4096" fill="black"/>'
svg+=''.join('<polygon fill="white" points="'+ ' '.join(f'{x},{y}' for x,y in p)+'"/>' for p in polygons)+'</svg>'
(P/'haste_rune_mask.svg').write_text(svg,encoding='utf-8')
mask=Image.new('L',(2048,8192),0);d=ImageDraw.Draw(mask)
for poly in polygons:d.polygon([(x*2,y*2) for x,y in poly],fill=255)
mask=mask.resize((1024,4096),Image.Resampling.LANCZOS)
mask.save(P/'T_Mask_haste_rune.png')
# Formal icon is imagegen output matching the approved metal-frame master.
# Keep the original editable vector mask; never regenerate the rejected flat frame.
import shutil
icon_source=P.parent/'RuneSymbolIcons20261009/Masters/blade_2_haste_rune.png'
shutil.copy2(icon_source,P/'blade_2_haste_rune.png')
(P/'design.json').write_text(json.dumps({'id':'haste_rune','name':'急速符文','slot':'blade_2','tier':'common','stats':{'attack_speed_mult':1.1},'description':'疾风折纹沿剑脊收束，黄色流光向剑尖掠过。','appearance':'疾风折纹 · 黄色流光','source':'Original project wind mask; current symbol-only framed icon from RuneSymbolIcons20261009','mask':'T_Mask_haste_rune.png','icon':'blade_2_haste_rune.png','visual_palette':'yellow core and yellow halo; independent haste mask with existing traveling-current timing','runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Haste rune vector mask exported and approved shared imagegen icon copied.')
