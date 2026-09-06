from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math
R=Path(__file__).resolve().parent;OUT=R/'previews';OUT.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
checks={}
for kind in ['modern','miner','runner']:
 data=json.loads((R/kind/'build-report.json').read_text())
 for clip in ['Idle','Walk','Attack','AttackRight','Death']:
  paths=sorted((R/'rendered'/(kind+'-after')/clip).glob('[0-9][0-9][0-9].png'))
  duration=data['clips'][clip];count=math.ceil(duration*24-1e-6);assert len(paths)>=count
  frames=[Image.open(p).convert('RGB').resize((600,540),Image.Resampling.LANCZOS) for p in paths[:count]]
  times=[round(min(i/24,duration)*100)*10 for i in range(count+1)]
  durations=[times[i+1]-times[i] for i in range(count)]
  out=OUT/(kind+'-'+clip+'.gif')
  frames[0].save(out,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)
  with Image.open(out) as gif:
   total=0
   for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
   assert gif.n_frames==count and abs(total/1000-duration)<.006
   checks[kind+'-'+clip]={'frames':count,'source_seconds':duration,'gif_seconds':total/1000}
  if clip in ['Attack','Death','Walk']:
   sheet=Image.new('RGB',(1200,885),'#18212b');draw=ImageDraw.Draw(sheet)
   draw.text((15,8),kind+' Low Poly V02 / '+clip,font=font,fill='white')
   for j in range(12):
    index=round(j*(len(paths)-1)/11)
    sheet.paste(Image.open(paths[index]).convert('RGB').resize((300,270)),((j%4)*300,45+(j//4)*280))
   sheet.save(OUT/(kind+'-'+clip+'-contact.jpg'),quality=91)
 for view in ['front','head-close','torso-close']:
  comp=Image.new('RGB',(1200,590),'#18212b');draw=ImageDraw.Draw(comp)
  for i,state in enumerate(['before','after']):
   comp.paste(Image.open(R/'rendered'/(kind+'-'+state)/(view+'.png')).convert('RGB').resize((600,540),Image.Resampling.LANCZOS),(i*600,50))
   draw.text((i*600+20,12),kind+' / '+('V01' if state=='before' else 'Low Poly V02'),font=font,fill='white')
  comp.save(OUT/(kind+'-'+view+'-comparison.jpg'),quality=94)
family=Image.new('RGB',(1800,590),'#18212b');draw=ImageDraw.Draw(family)
for i,kind in enumerate(['modern','miner','runner']):
 family.paste(Image.open(R/'rendered'/(kind+'-after')/'front.png').convert('RGB').resize((600,540),Image.Resampling.LANCZOS),(i*600,50))
 draw.text((i*600+20,12),kind+' / Low Poly V02',font=font,fill='white')
family.save(OUT/'family-v02.jpg',quality=94)
(OUT/'validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print('DETAIL_PREVIEW_PARITY_PASS',len(checks))
