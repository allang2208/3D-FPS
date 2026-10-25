from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/RefineV2/ReviewSaved')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
names={'Chair':'椅子','Sofa':'沙发','Bed':'床铺','Bunk':'下铺'}
phases={'Enter':'进入','Idle':'保持','Exit':'起身'}
frames={};timeline={}
for k in names:
 timeline[k]=json.loads((ROOT/(k+'_timeline.json')).read_text())
 frames[k]=[]
 for i,p in enumerate(sorted((ROOT/'frames'/k).glob('*.png'))):
  im=Image.new('RGB',(600,650),(29,35,42));im.paste(Image.open(p).convert('RGB'),(0,42));d=ImageDraw.Draw(im)
  phase,t=timeline[k][i];d.text((18,7),names[k]+' · '+phases[phase],font=font,fill=(240,243,248))
  d.text((18,619),'当前已保存动作 | 中性材质离线预览',font=small,fill=(202,210,221));frames[k].append(im)
 duration=[80 if i%3!=2 else 90 for i in range(len(frames[k]))]
 palette=frames[k][len(frames[k])//2].quantize(colors=192)
 q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames[k]]
 q[0].save(ROOT/(k+'.gif'),save_all=True,append_images=q[1:],duration=duration,loop=0,disposal=2,optimize=True)
for label,pair in [('sitting_review',('Chair','Sofa')),('lying_review',('Bed','Bunk'))]:
 sequence=[]
 for i in range(max(len(frames[k]) for k in pair)):
  im=Image.new('RGB',(1200,650))
  for j,k in enumerate(pair):im.paste(frames[k][min(i,len(frames[k])-1)],(600*j,0))
  sequence.append(im.resize((1000,542),Image.Resampling.LANCZOS))
 palette=sequence[len(sequence)//2].quantize(colors=192)
 q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in sequence]
 q[0].save(ROOT/(label+'.gif'),save_all=True,append_images=q[1:],duration=[80 if i%3!=2 else 90 for i in range(len(q))],loop=0,disposal=2,optimize=True)
sheet=Image.new('RGB',(1200,1300),(29,35,42))
for row,k in enumerate(names):
 indices=[0,round((len(frames[k])-1)*.25),next(i for i,x in enumerate(timeline[k]) if x[0]=='Idle'),len(frames[k])-8]
 for col,index in enumerate(indices):sheet.paste(frames[k][index].resize((300,325)),(col*300,row*325))
sheet.save(ROOT/'contact_sheet.jpg',quality=92)
print('GIFS_SAVED',[(p.name,p.stat().st_size) for p in ROOT.glob('*.gif')])
