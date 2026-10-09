"""Native glyph layout for each physical plate ratio. Never resize text artwork."""
import json,runpy,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
power=runpy.run_path(str(ROOT.parent/'Scripts/prepare_chinese_signs.py'))
power={a.key:([a.title,a.subtitle] if a.subtitle else [a.title],a.style,a.icon) for a in power['LABELS']}
cabinet=runpy.run_path(str(ROOT.parent/'Scripts/prepare_chinese_cabinet_overlay.py'))['CELL_TEXT']
regular=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
bold=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Medium.otf'
cards=json.loads((ROOT/'cards.json').read_text('utf8'))
image=Image.new('RGB',(4096,4096),(31,43,36));layouts={};x=y=20;row=0
for c in cards:
 key=(c['family'],c['key'],c['width'],c['height'])
 if key in layouts:
  c.update(layouts[key]);continue
 if c['family']=='power':lines,style,icon=power[c['key']]
 elif c['family']=='cabinet':lines,style,icon=cabinet[c['key']],'ivory',''
 else:lines,style,icon=['数据系统 · 04号机柜','检修前切断主电源'],'ivory',''
 w=1024 if c['width']>=1 else 640
 h=round(w*c['height']/c['width'])
 # Pixel edge is cropped by a subpixel amount to match physical dimensions exactly.
 sample_h=w*c['height']/c['width'];h=math.ceil(sample_h)
 if x+w+20>4096:x=20;y+=row+32;row=0
 if y+h+20>4096:raise RuntimeError('Text atlas needs a new page; do not shrink glyph artwork')
 bg=(64,81,66) if style=='green' else (190,173,112) if style=='yellow' else (197,199,179)
 ink=(207,211,191) if style=='green' else (31,43,36)
 art=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(art)
 pad=max(9,int(min(w,h)*.08));rim=max(2,round(min(w,h)*.012))
 d.rectangle((rim,rim,w-rim-1,h-rim-1),outline=ink,width=rim)
 fields=[];left=pad+3
 if icon:
  size=min(h*.52,w*.13);cx=pad+size*.6;cy=h*.5
  if icon=='arrow':
   d.polygon([(cx-size*.45,cy-size*.11),(cx+size*.05,cy-size*.11),(cx+size*.05,cy-size*.34),(cx+size*.48,cy),(cx+size*.05,cy+size*.34),(cx+size*.05,cy+size*.11),(cx-size*.45,cy+size*.11)],fill=ink)
  else:
   d.polygon([(cx,cy-size*.48),(cx-size*.48,cy+size*.40),(cx+size*.48,cy+size*.40)],outline=ink,width=max(3,rim))
   d.line((cx,cy-size*.17,cx,cy+size*.09),fill=ink,width=max(3,rim));d.ellipse((cx-rim,cy+size*.21-rim,cx+rim,cy+size*.21+rim),fill=ink)
  left=int(pad+size*1.2)
 avail=h-2*pad;weights=[1.25]+[1]*(len(lines)-1);unit=avail/sum(weights);yy=pad
 for i,(line,weight) in enumerate(zip(lines,weights)):
  band=unit*weight;fs=max(6,int(band*.78));path=bold if i==0 else regular
  while True:
   font=ImageFont.truetype(str(path),fs);bb=font.getbbox(line)
   if bb[2]-bb[0]<=w-pad-left and bb[3]-bb[1]<=band*.84:break
   fs-=1
   if fs<6:raise RuntimeError('Plate text is too small: '+str(key))
  tx=left+(w-pad-left-(bb[2]-bb[0]))/2-bb[0];ty=yy+(band-(bb[3]-bb[1]))/2-bb[1]
  d.text((tx,ty),line,font=font,fill=ink)
  fields.append(dict(text=line,font_size_px=fs));yy+=band
 ImageDraw.Draw(image).rectangle((x-12,y-12,x+w+12,y+h+12),fill=bg)
 image.paste(art,(x,y));layout=dict(rect=[x,y,x+w,y+sample_h],text=fields)
 layouts[key]=layout;c.update(layout);x+=w+32;row=max(row,h)
image.save(OUT/'T_Power_TextCards.png')
(ROOT/'cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'atlas.json').write_text(json.dumps(dict(size=[4096,4096],unique_layouts=len(layouts),cards=cards,fonts=[str(regular),str(bold)],raster_resized=False),ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_TEXT_ART_AUTHORED',len(layouts),'native ratio layouts')
