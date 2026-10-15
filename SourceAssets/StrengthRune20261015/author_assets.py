"""Original vector rune artwork, its runtime mask, and the requested red design sheet."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFilter, ImageFont

P=Path(__file__).resolve().parent
P.mkdir(parents=True,exist_ok=True)
# Broad angular shoulders brace a continuous axial core. All polygons share
# one editable source; the framed icon receives this same core as its reference.
core=[
 [(-27,38),(0,0),(27,38),(19,145),(-19,145)],
 [(-19,160),(0,138),(19,160),(19,370),(0,405),(-19,370)],
 [(-45,177),(-115,122),(-176,148),(-175,254),(-139,284),(-140,180),(-114,171),(-45,225)],
 [(-42,256),(-117,306),(-117,371),(-80,400),(-80,329),(-42,304)],
 [(-39,398),(-85,438),(-85,477),(-28,448),(-19,526),(0,566),(19,526),(28,448),(85,477),(85,438),(39,398),(0,435)],
 [(-158,336),(-184,367),(-157,398),(-137,367)],
]
core += [[(-x,y) for x,y in poly] for poly in core[2:4]]
core += [[(-x,y) for x,y in core[5]]]
polys=[]
for poly in core:
    polys.append([(512+x*.86,2720+y*.86) for x,y in poly])
# A single rising spine, separated by deliberate pauses and uneven braces.
polys += [
 [(512,340),(533,530),(526,1020),(512,1060),(498,1020),(491,530)],
 [(498,1140),(512,1108),(526,1140),(526,1760),(512,1790),(498,1760)],
 [(498,1880),(512,1848),(526,1880),(526,2560),(512,2630),(498,2560)],
 [(459,820),(483,862),(483,1040),(512,1080),(541,1040),(541,862),(565,820),(565,1054),(512,1122),(459,1054)],
 [(442,1550),(470,1580),(470,1740),(512,1808),(554,1740),(554,1580),(582,1550),(582,1752),(512,1854),(442,1752)],
 [(455,2220),(478,2250),(478,2425),(512,2480),(546,2425),(546,2250),(569,2220),(569,2440),(512,2522),(455,2440)],
 [(512,3280),(536,3312),(512,3350),(488,3312)],
 [(498,3410),(526,3410),(523,3630),(512,3770),(501,3630)]
]
def draw_polys(size, polygons, scale=1, offset=(0,0)):
    im=Image.new('L',(size[0]*2,size[1]*2),0);d=ImageDraw.Draw(im)
    for p in polygons:d.polygon([((x*scale+offset[0])*2,(y*scale+offset[1])*2) for x,y in p],fill=255)
    return im.resize(size,Image.Resampling.LANCZOS)
mask=draw_polys((1024,4096),polys)
mask.save(P/'T_Mask_strength_rune.png')
svg='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="4096" viewBox="0 0 1024 4096"><rect width="1024" height="4096" fill="black"/>'
svg+=''.join('<polygon fill="white" points="'+' '.join(f'{x:g},{y:g}' for x,y in p)+'"/>' for p in polys)+'</svg>'
(P/'strength_rune_mask.svg').write_text(svg,encoding='utf-8')
glyph=draw_polys((768,896),core,1.25,(384,84))
glyph.save(P/'StrengthRune_CoreReference.png')

def red_ink(mask):
    base=Image.new('RGB',mask.size,(15,17,20))
    base.paste((107,9,13),mask=mask.filter(ImageFilter.GaussianBlur(15)))
    base.paste((215,19,25),mask=mask.filter(ImageFilter.GaussianBlur(4)))
    base.paste((246,41,42),mask=mask)
    return base
sheet=Image.new('RGB',(1440,1180),(15,17,20))
sheet.paste(red_ink(glyph),(85,205))
strip=mask.resize((225,900),Image.Resampling.LANCZOS)
sheet.paste(red_ink(strip),(1030,185))
d=ImageDraw.Draw(sheet)
font=lambda s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s)
d.text((72,48),'力量符文',font=font(48),fill=(229,231,232))
d.text((75,117),'物理伤害 +10%',font=font(27),fill=(245,69,67))
d.line((925,205,925,1030),fill=(47,48,51),width=2)
d.text((290,1100),'核心符印',font=font(23),fill=(175,180,185))
d.text((1037,1100),'完整贴附纹样',font=font(23),fill=(175,180,185))
sheet.save(P/'StrengthRune_Design.png')
option={'id':'strength_rune','name':'力量符文','tier':'common',
 'description':'粗壮中轴连接双肩折纹，赤红微光沿短刻纹汇入主印。',
 'appearance':'中轴重印 · 赤红微光',
 'stats':{'physical_damage_mult':1.1},
 'effects':[{'text':'物理伤害 +10%','benefit':1}],'special_effects':[]}
(P/'option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STRENGTH_RUNE_ARTWORK_AUTHORED')
