from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
out=R/'previews';out.mkdir(exist_ok=True)
report={}
for variant in ['miner','runner']:
 data=json.loads((R/variant/'build-report.json').read_text())
 for clip in ['Idle','Walk','Attack','AttackRight','Death']:
  duration=data['clips'][clip]
  paths=sorted((R/'rendered'/variant/clip).glob('[0-9][0-9][0-9].png'))
  count=math.ceil(duration*24-1e-6)
  assert len(paths)>=count
  frames=[Image.open(p).convert('RGB').resize((600,540),Image.Resampling.LANCZOS) for p in paths[:count]]
  time=[round(min(i/24,duration)*100)*10 for i in range(count+1)]
  durations=[time[i+1]-time[i] for i in range(count)]
  target=out/(variant+'-'+clip+'.gif')
  frames[0].save(target,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)
  with Image.open(target) as gif:
   ms=0
   for i in range(gif.n_frames):gif.seek(i);ms+=gif.info['duration']
   assert abs(ms/1000-duration)<.006 and gif.n_frames==count
   report[variant+'-'+clip]={'frames':count,'source_seconds':duration,'gif_seconds':ms/1000}
  sheet=Image.new('RGB',(1200,900),'#18212b');draw=ImageDraw.Draw(sheet)
  draw.text((16,8),variant.title()+' / '+clip+' / Actual Godot model',font=font,fill='white')
  for j in range(12):
   idx=round(j*(len(paths)-1)/11)
   img=Image.open(paths[idx]).convert('RGB').resize((300,270),Image.Resampling.LANCZOS)
   x,y=(j%4)*300,45+(j//4)*285
   sheet.paste(img,(x,y));draw.text((x+5,y+5),f'{min(idx/24,duration):.2f}s',font=small,fill='white')
  sheet.save(out/(variant+'-'+clip+'-contact.jpg'),quality=92)
comparison=Image.new('RGB',(1800,585),'#18212b');draw=ImageDraw.Draw(comparison)
sources=[(R.parent/'modern-zombie-v01-20260906/rendered/modern/front.png','Modern zombie'),(R/'rendered/miner/front.png','Workwear miner'),(R/'rendered/runner/front.png','Runner')]
for i,(path,title) in enumerate(sources):
 comparison.paste(Image.open(path).convert('RGB').resize((600,540),Image.Resampling.LANCZOS),(i*600,45))
 draw.text((i*600+18,10),title,font=font,fill='white')
comparison.save(out/'family-comparison.jpg',quality=94)
(out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('VARIANT_PREVIEWS_VALIDATED',len(report))
