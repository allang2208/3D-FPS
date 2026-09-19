from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).parent/'Review'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
comparison=Image.new('RGB',(1280,426),(28,31,36));draw=ImageDraw.Draw(comparison)
draw.text((16,8),'右腕衔接对比 · 0.167 秒接触帧 · 作者源模型预览',font=font,fill='white')
for i,(rev,title) in enumerate((('M','M：原腕部折角'),('N','N：握持换向，前臂接到手掌'))):
    im=Image.open(P/f'{rev}_Base_fp_020.png').convert('RGB').resize((640,360))
    comparison.paste(im,(i*640,42));draw.text((i*640+14,402),title,font=small,fill='white')
comparison.save(P/'before_after.jpg',quality=88)
profiles=('Base','Drum','Angled','Vertical','Canted','Prism')
sheet=Image.new('RGB',(1440,600),(28,31,36));draw=ImageDraw.Draw(sheet)
for i,profile in enumerate(profiles):
    im=Image.open(P/f'N_{profile}_wrist_020.png').convert('RGB').resize((480,270))
    x=(i%3)*480;y=(i//3)*300;sheet.paste(im,(x,y));draw.text((x+12,y+272),profile+' / N / 0.167 s',font=small,fill='white')
sheet.save(P/'six_profiles.jpg',quality=88)
frames=[Image.open(P/f'N_Base_fp_{f:03}.png').convert('RGB') for f in range(0,109,4)]
timeline=Image.new('RGB',(1440,702),(28,31,36));draw=ImageDraw.Draw(timeline)
for i,f in enumerate((0,4,8,12,16,20,32,56,72,88,96,108)):
    x=(i%4)*360;y=(i//4)*234
    im=Image.open(P/f'N_Base_fp_{f:03}.png').convert('RGB').resize((360,203));timeline.paste(im,(x,y))
    draw.text((x+8,y+207),f'N / {f/120:.3f} s',font=small,fill='white')
timeline.save(P/'timeline.jpg',quality=88)
gif=[im.resize((640,360)).quantize(colors=128) for im in frames]
gif[0].save(P/'N_motion.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*9+[33],loop=0,optimize=False)
print('REVIEW_DELIVERY_READY')
