"""Explicitly requested bow attachment icon audit; never starts the game."""
import hashlib, json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
P=Path(__file__).resolve().parent; ROOT=P.parents[1]
D=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
catalog=json.loads((ROOT/'Content/ColdSteelData/bow-gunsmith.json').read_text(encoding='utf-8-sig'))
phase=sys.argv[1] if len(sys.argv)>1 else 'before'
if phase=='candidate':D=P/'Icons'
out=P/(phase+'-audit.json')
if phase=='before' and out.exists():raise RuntimeError('Do not overwrite baseline')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
sheet=Image.new('RGB',(1500,5*246),(26,29,32)); draw=ImageDraw.Draw(sheet)
rows=[]
for i,col in enumerate(catalog['columns']):
    options=[('category_'+col['key'],col['name']+' · 分类',col['factory_visual']),
             (col['key']+'_false',col['default'],col['factory_visual'])]
    for o in col['options']:
        options.append((col['key']+'_'+o['id'],o['name'],dict(col['factory_visual'],**o.get('visual',{}))))
    for j,(suffix,label,visual) in enumerate(options):
        name='bow_dark_'+suffix; candidate=D/(name+'.png')
        resolved=candidate if candidate.exists() else D/(suffix+'.png')
        row=dict(name=name,label=label,slot=col['key'],resolved=str(resolved),weapon_specific=resolved==candidate,visual=visual)
        x=j*250;y=i*246
        draw.rectangle((x+3,y+3,x+246,y+241),fill=(37,40,44))
        draw.text((x+10,y+9),label,font=font,fill=(225,225,225))
        if resolved.exists():
            im=Image.open(resolved).convert('RGBA'); a=np.asarray(im);mask=a[:,:,3]>32
            delta=a[:,:,:3].max(2).astype(int)-a[:,:,:3].min(2).astype(int)
            row.update(size=list(im.size),sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
                alpha_bbox=im.getchannel('A').getbbox(),colored_fraction=float((delta[mask]>3).mean()),
                max_rgb_delta=int(delta[mask].max()),ue_asset_exists=resolved.with_suffix('.uasset').exists())
            thumb=im.copy();thumb.thumbnail((162,170),Image.Resampling.LANCZOS)
            sheet.paste(thumb,(x+14+(162-thumb.width)//2,y+42+(170-thumb.height)//2),thumb)
            for size,yy in [(48,59),(64,137)]:
                mini=im.resize((size,size),Image.Resampling.LANCZOS)
                sheet.paste(mini,(x+181+(64-size)//2,y+yy),mini)
                draw.text((x+187,y+yy+size+2),str(size)+' px',font=small,fill=(160,160,160))
        else:row['missing']=True
        draw.text((x+10,y+220),suffix,font=small,fill=(150,155,160))
        rows.append(row)
sheet.save(P/(phase+'-contact-sheet.png'))
out.write_text(json.dumps(dict(phase=phase,count=len(rows),icons=rows,gameplay_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(phase=phase,count=len(rows),colored=sum(r.get('colored_fraction',0)>.01 for r in rows),missing=sum(r.get('missing',False) for r in rows),sheet=str(P/(phase+'-contact-sheet.png')))))
