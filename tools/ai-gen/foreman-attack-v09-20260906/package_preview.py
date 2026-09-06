from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
R=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',17)
report={}
delays=[round((i+1)*150/36)*10-round(i*150/36)*10 for i in range(36)]
for view,name in [('body','Attack-comparison'),('side','Whip-comparison')]:
    height=480 if view=='body' else 360
    frames=[]
    for i in range(36):
        panel=Image.new('RGB',(1280,height+44),(24,28,32))
        d=ImageDraw.Draw(panel)
        for j,(version,label) in enumerate([('v08','V08 原版'),('v09','V09 攻击重做')]):
            im=Image.open(R/'rendered'/f'{version}-{view}'/f'{i:03d}.png').convert('RGB')
            assert im.size==((960,720) if view=='body' else (1280,720)),im.size
            im=im.resize((640,height),Image.Resampling.LANCZOS)
            panel.paste(im,(j*640,44))
            d.text((j*640+18,11),label,font=font,fill='white')
        d.text((455,15),f'{i/24:.3f} s',font=small,fill=(190,205,216))
        frames.append(panel)
    frames[0].save(R/(name+'.gif'),save_all=True,append_images=frames[1:],duration=delays,loop=0,disposal=2,optimize=True)
    gif=Image.open(R/(name+'.gif'))
    total=0
    for i in range(gif.n_frames):
        gif.seek(i);total+=gif.info['duration']
    assert total==1500
    report[name]={'frames':gif.n_frames,'duration_ms':total,'same_camera_lighting':True}
    for page in range(3):
        sheet=Image.new('RGB',(1536,906),(24,28,32))
        draw=ImageDraw.Draw(sheet)
        for j in range(12):
            i=page*12+j
            im=Image.open(R/'rendered'/f'v09-{view}'/f'{i:03d}.png').convert('RGB')
            im.thumbnail((384,288),Image.Resampling.LANCZOS)
            x,y=j%4*384,j//4*302
            sheet.paste(im,(x,y))
            draw.text((x+4,y+282),f'{i:02d}: {i/24:.3f}s',font=small,fill='white')
        sheet.save(R/f'v09-{view}-frames-{page}.jpg',quality=92)
    contact=Image.new('RGB',(1280,height+44),(24,28,32));d=ImageDraw.Draw(contact)
    for j,version in enumerate(['v08','v09']):
        im=Image.open(R/'rendered'/f'{version}-{view}'/'contact.png').convert('RGB').resize((640,height),Image.Resampling.LANCZOS)
        contact.paste(im,(j*640,44));d.text((j*640+18,11),f'{version.upper()}  接触 0.59625 s',font=font,fill='white')
    contact.save(R/f'contact-{view}.jpg',quality=94)
(R/'preview-report.json').write_text(json.dumps(report,indent=2))
print('FOREMAN_V09_PREVIEWS_COMPLETE',json.dumps(report))
