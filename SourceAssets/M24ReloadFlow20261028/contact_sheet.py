from pathlib import Path
from PIL import Image,ImageDraw
import json
O=Path(__file__).resolve().parent
for role in ('reload','reload_mag10'):
 for kind,frames in [('fps',[20,22,24.5,25.25,26,27,30,33,35,38,42,46]),('hand',[24.5,25.25,26,35,40,42])]:
  size=(400,225) if kind=='fps' else (480,270);cols=3;rows=(len(frames)+cols-1)//cols
  sheet=Image.new('RGB',(cols*size[0],rows*(size[1]+24)),(28,30,34));draw=ImageDraw.Draw(sheet)
  for i,f in enumerate(frames):
   img=Image.open(O/'Review'/(role+'_'+str(f)+('_hand' if kind=='hand' else '')+'.png')).resize(size)
   x=(i%cols)*size[0];y=(i//cols)*(size[1]+24);sheet.paste(img,(x,y+24));draw.text((x+8,y+5),f'{role} source frame {f}',fill='white')
  sheet.save(O/(role+'_'+kind+'_sheet.jpg'),quality=92)
data=json.loads((O/'review_geometry.json').read_text())
print({role:max(x['top_margin_cm'] for x in val['reset_visible_samples']) for role,val in data.items()})
