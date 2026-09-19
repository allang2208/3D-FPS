from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;s=(O.parent/'AKMReloadPolish20260911/delivery.py').read_text()
s=s.replace("['akm-polish-angled-v1','akm-polish-side-v2']","['akm-arm-prism-final','akm-arm-angled-final']")
s=s.replace("[('drum_normal','returned_10'),('drum_empty','returned_12')]","[('standard_normal','returned_6'),('standard_empty','returned_8'),('drum_normal','returned_10'),('drum_empty','returned_12')]")
s=s.replace("('side' if 'side' in run else 'first_person')","('angled' if 'angled' in run else 'prism')")
exec(compile(s,str(O/'delivery.py'),'exec'))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
sheet=Image.new('RGB',(1200,920),'#171b21');draw=ImageDraw.Draw(sheet)
for row,variant in enumerate(['prism','angled']):
 for col,phase in enumerate(['before','after']):
  x,y=col*600,row*460;sheet.paste(Image.open(O/f'{variant}_{phase}.png').resize((600,420)),(x,y+40));draw.text((x+12,y+6),('短握把' if variant=='prism' else '斜握把')+('：调整前' if phase=='before' else '：肩肘支撑调整后'),font=font,fill='white')
sheet.save(O/'Delivery/arm-comparison.jpg',quality=94)
S=O.parents[1]/'Saved/ForegripAudit'
for name,run in [('prism','akm-arm-prism-final'),('angled','akm-arm-angled-final')]:
 for image in ['idle','wrist_review','optic_mount_review']:
  Image.open(S/run/(image+'.png')).convert('RGB').save(O/'Delivery'/(name+'_'+image+'.jpg'),quality=94)
