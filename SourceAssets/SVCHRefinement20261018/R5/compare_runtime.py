import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;P=O.parents[2]
old=P/'Saved/SVCHPoseAudit/svch-check-20261018-r4-correctives'
new=P/'Saved/SVCHPoseAudit'/sys.argv[1]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
sheet=Image.new('RGB',(1280,860),(27,29,33));draw=ImageDraw.Draw(sheet)
selections=[]
for col,(root,label) in enumerate(((old,'R4 修复前'),(new,'R5 修复后'))):
    rows=[json.loads(line) for line in (root/'frames.jsonl').read_text(encoding='utf-8-sig').splitlines() if line]
    for row,(stage,t,crop,caption) in enumerate((('ads',1.47,(530,280,750,680),'机械瞄具'),('inspect',3.73,(530,350,1160,710),'检视翻腕'))):
        capture=min((r for r in rows if r['stage']==stage),key=lambda r:abs(r['stage_time']-t))
        img=Image.open(root/'Frames'/capture['image']).convert('RGB').crop(crop)
        img.thumbnail((620,385),Image.Resampling.LANCZOS)
        x,y=col*640,row*430
        sheet.paste(img,(x+(640-img.width)//2,y+40+(385-img.height)//2))
        draw.text((x+14,y+9),label+' · '+caption,font=font,fill=(238,238,238))
        selections.append({'revision':label,'stage':stage,'image':capture['image'],'stage_time':capture['stage_time']})
sheet.save(O/'r4-r5-comparison.jpg',quality=94)
(O/'comparison_frames.json').write_text(json.dumps(selections,ensure_ascii=False,indent=1),encoding='utf-8')
print(O/'r4-r5-comparison.jpg')

# Same cameras and neutral clay isolate the geometry changes from PBR shading.
detail=Image.new('RGB',(1200,1540),(27,29,33));dd=ImageDraw.Draw(detail)
for col,version in enumerate(('R4','R5')):
    for row,(part,title) in enumerate((('rear','照门孔环'),('front','准星护翼'),('muzzle','枪口制退器'))):
        src=O/f'{version}_{part}_clay.png'
        if not src.exists():continue
        img=Image.open(src).convert('RGB');img.thumbnail((600,480),Image.Resampling.LANCZOS)
        x,y=600*col,row*510
        detail.paste(img,(x,y+30))
        dd.text((x+12,y+4),version+' · '+title,font=font,fill=(238,238,238))
detail.save(O/'r4-r5-mechanisms-clay.jpg',quality=94)
