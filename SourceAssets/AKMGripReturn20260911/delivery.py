from pathlib import Path
O=Path(__file__).parent;s=(O.parent/'AKMReloadPolish20260911/delivery.py').read_text()
s=s.replace("['akm-polish-angled-v1','akm-polish-side-v2']","['akm-return-prism-v1','akm-return-angled-v2']")
s=s.replace("[('drum_normal','returned_10'),('drum_empty','returned_12')]","[('standard_normal','returned_6'),('standard_empty','returned_8'),('drum_normal','returned_10'),('drum_empty','returned_12')]")
s=s.replace("('side' if 'side' in run else 'first_person')","('angled' if 'angled' in run else 'prism')")
exec(compile(s,str(O/'delivery.py'),'exec'))
from PIL import Image,ImageDraw,ImageFont
sheet=Image.new('RGB',(1200,440),'#171b21');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
for i,phase in enumerate(['before','after']):
 sheet.paste(Image.open(O/f'prism_{phase}_reload_330.png').resize((600,400)),(i*600,40));draw.text((i*600+12,6),'修正前：先回到护木' if i==0 else '修正后：直接握住当前握把',font=font,fill='white')
sheet.save(O/'Delivery/direct-return.jpg',quality=93)
