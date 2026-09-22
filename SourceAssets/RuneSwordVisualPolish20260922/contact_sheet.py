"""Assemble the delivered transparent icons into one readable production sheet."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
rows=[r for r in json.loads((P/'icon_manifest.json').read_text(encoding='utf-8')) if r['id']!='category']
cell=280;sheet=Image.new('RGB',(cell*6,cell*math.ceil(len(rows)/6)),(29,32,37))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16);draw=ImageDraw.Draw(sheet)
for i,row in enumerate(rows):
    x=(i%6)*cell;y=(i//6)*cell
    icon=Image.open(P/'Icons'/(row['key']+'.png')).convert('RGBA');icon.thumbnail((cell-20,cell-50))
    sheet.paste(icon,(x+(cell-icon.width)//2,y+(cell-40-icon.height)//2),icon)
    draw.text((x+12,y+cell-32),row['name'],font=font,fill=(225,229,235))
sheet.save(P/'icon_contact_sheet.jpg',quality=92)
print('ICON_CONTACT_SHEET_WRITTEN')
