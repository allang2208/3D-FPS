"""Package generated RGBA art into the existing 1024 px UI texture contract."""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
rows=json.loads((P/'generated_sources.json').read_text(encoding='utf-8'))
RAW=P/'Generated';OUT=P/'Icons';RAW.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
receipt=[]
for row in rows:
    source=Path(row['source']);raw=RAW/(row['id']+'.png');shutil.copy2(source,raw)
    im=Image.open(raw)
    if im.mode!='RGBA':raise RuntimeError('Generator must provide RGBA transparency: '+str(raw))
    alpha=im.getchannel('A');box=alpha.getbbox()
    if not box or alpha.getextrema()[0]!=0:raise RuntimeError('Generator did not provide a transparent cutout: '+str(raw))
    # Packing only: preserve generated color/alpha and aspect, fit the full subject.
    subject=im.crop(box);subject.thumbnail((840,840),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(1024,1024),(0,0,0,0));canvas.paste(subject,((1024-subject.width)//2,(1024-subject.height)//2))
    target=OUT/(row['key']+'.png');canvas.save(target)
    receipt.append({**row,'raw':str(raw),'source_alpha_bounds':box,'original_size':im.size,'output':str(target),'output_size':[1024,1024],'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
shutil.copy2(OUT/'ue_rune_sword_blade_2_false.png',OUT/'ue_rune_sword_category_blade_2.png')
(P/'packaging_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
# One overview for the delivered set; the actual UI PNGs contain no text or plate.
sheet=Image.new('RGB',(1400,320),(27,30,36));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
for i,row in enumerate(rows):
    icon=Image.open(OUT/(row['key']+'.png'));icon.thumbnail((260,260),Image.Resampling.LANCZOS)
    sheet.paste(icon,(i*280+10,3),icon)
    draw.text((i*280+24,280),row['name'],font=font,fill=(225,230,237))
sheet.save(P/'semantic_icons.jpg',quality=94)
print('SEMANTIC_ICONS_PACKAGED',len(rows)+1)
