"""Contact sheets for the user's specifically requested M24 icon inspection."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
P=O.parents[1]
I=O/'Icons'
F=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
rows=json.loads((I/'production.json').read_text())
labels=['骨架狙击枪托','M24 原装栓机','碳纤维轻型栓机','M24 原装握持区','先进枪机系统','M24 原装枪身','M24 原装枪托','SVCH 原装枪托']
sheet=Image.new('RGB',(1120,704),(29,30,32));draw=ImageDraw.Draw(sheet)
for n,row in enumerate(rows):
    x=(n%4)*280;y=(n//4)*352
    im=Image.open(I/(row['key']+'.png')).convert('RGBA')
    sheet.paste(im.resize((236,236),Image.Resampling.LANCZOS),(x+22,y+6),im.resize((236,236),Image.Resampling.LANCZOS))
    draw.text((x+12,y+246),labels[n],font=font,fill='white')
    for size,off in [(64,12),(48,98)]:
        t=im.resize((size,size),Image.Resampling.LANCZOS);sheet.paste(t,(x+off,y+278),t)
    draw.text((x+169,y+287),'64 / 48 px',font=small,fill='#cccccc')
sheet.save(I/'updated_contact_sheet.png')
catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8'))
m24=next(r for r in catalog['weapons'] if r['id']=='ue_m24')
categories=[]
for slot in m24['allowed']:
    key='category_'+slot
    path=F/(key+'.png')
    if not path.exists():
        key='ue_m24_category_'+slot;path=F/(key+'.png')
    if not path.exists():path=F.parent/(key+'.png')
    categories.append(dict(slot=slot,path=str(path),exists=path.exists()))
(I/'category_mapping.json').write_text(json.dumps(categories,indent=2))
sheet=Image.new('RGB',(len(categories)*150,210),(29,30,32));draw=ImageDraw.Draw(sheet)
for n,row in enumerate(categories):
    draw.text((n*150+6,155),row['slot'],font=small,fill='white')
    if row['exists']:
        im=Image.open(row['path']).convert('RGBA').resize((140,140),Image.Resampling.LANCZOS);sheet.paste(im,(n*150+5,5),im)
sheet.save(I/'categories_before.png')
print('Saved updated_contact_sheet.png, categories_before.png and category_mapping.json')
