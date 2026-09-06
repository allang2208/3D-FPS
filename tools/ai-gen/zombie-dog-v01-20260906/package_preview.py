from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
R=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',26)
small=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',18)
specs={'Idle':3333.333333,'Gallop':566.666667,'Attack':1333.333333,'Death':1066.666667}
report={}
for clip,duration in specs.items():
    frames=[]
    paths=sorted((R/'rendered/zombie'/clip).glob('[0-9]*.png'))
    for p in paths[:-1]:
        im=Image.open(p).convert('RGB');im.thumbnail((880,640),Image.Resampling.LANCZOS);frames.append(im)
    n=len(frames);delays=[round((i+1)*duration/n/10)*10-round(i*duration/n/10)*10 for i in range(n)]
    frames[0].save(R/(clip+'.gif'),save_all=True,append_images=frames[1:],duration=delays,loop=0,disposal=2,optimize=True)
    gif=Image.open(R/(clip+'.gif'));total=0
    for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
    assert abs(total-duration)<=5,(clip,total,duration)
    report[clip]={'source_seconds':duration/1000,'gif_duration_ms':total,'gif_frames':gif.n_frames,'existing_animation':True}
    for page in range((n+11)//12):
        sheet=Image.new('RGB',(1320,1035),(23,27,31));draw=ImageDraw.Draw(sheet)
        for j in range(12):
            i=page*12+j
            if i>=n:break
            im=frames[i].copy();im.thumbnail((440,315));x=j%3*440;y=j//3*258
            im.thumbnail((440,230));sheet.paste(im,(x,y));draw.text((x+8,y+234),f'{clip} {i/24:.3f}s',font=small,fill='white')
        sheet.save(R/f'{clip}-frames-{page}.jpg',quality=91)
for view in ['left','right']:
    sheet=Image.new('RGB',(1600,632),(23,27,31));draw=ImageDraw.Draw(sheet)
    for j,(version,label) in enumerate([('source','原黑狼'),('zombie','僵尸犬 · 现有骨架与动作')]):
        im=Image.open(R/'rendered'/version/(view+'.png')).convert('RGB').resize((800,582),Image.Resampling.LANCZOS)
        sheet.paste(im,(j*800,50));draw.text((j*800+20,13),label,font=font,fill='white')
    sheet.save(R/f'comparison-{view}.jpg',quality=95)
sheet=Image.new('RGB',(1600,1200),(23,27,31));draw=ImageDraw.Draw(sheet)
for j,view in enumerate(['left','right','front','side']):
    im=Image.open(R/'rendered/zombie'/(view+'.png')).convert('RGB').resize((800,582),Image.Resampling.LANCZOS)
    sheet.paste(im,(j%2*800,j//2*600))
sheet.save(R/'zombie-dog-review.jpg',quality=95)
(R/'preview-report.json').write_text(json.dumps(report,indent=2));print('ZOMBIE_DOG_PREVIEWS_COMPLETE',json.dumps(report))
