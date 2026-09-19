from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import shutil,json
O=Path(__file__).parent;P=O.parents[1];D=O/'Delivery';D.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',21)
shots=[('AKM / holographic + suppressor',P/'Saved/ForegripAudit/akm-angled-final/idle.png'),('ADS',P/'Saved/ForegripAudit/akm-angled-final/ads.png'),('Prism handstop',P/'Saved/ForegripAudit/akm-prism-v2/grasp_closeup.png'),('Angled foregrip / fitted rail',P/'Saved/ForegripAudit/akm-angled-final/grasp_closeup.png')]
sheet=Image.new('RGB',(1200,900),'#15191f');draw=ImageDraw.Draw(sheet)
for i,(label,p) in enumerate(shots):
 x=i%2*600;y=i//2*450;sheet.paste(Image.open(p).convert('RGB').resize((600,420)),(x,y+30));draw.text((x+10,y+4),label,font=font,fill='white')
sheet.save(D/'AKM-attachments-runtime.jpg',quality=92)
for prefix in ['standard_normal','drum_empty']:
 files=sorted((P/'Saved/ForegripAudit/akm-angled-final').glob(prefix+'_*.png'));frames=[Image.open(p).convert('RGB').resize((600,420)) for p in files]
 durations=[max(30,round((b.stat().st_mtime-a.stat().st_mtime)*1000)) for a,b in zip(files,files[1:])]+[1000]
 frames[0].save(D/(prefix+'.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0)
icons=P/'Saved/WeaponIcons'
for n in range(4):
 p=max(icons.glob(f'variant-{n}-*.png'),key=lambda p:p.stat().st_mtime);shutil.copy2(p,D/f'configuration-{n}.png')
print('AKM_DELIVERY_PASS')
