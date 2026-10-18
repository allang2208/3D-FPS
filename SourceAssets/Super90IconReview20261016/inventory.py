"""Snapshot the actual SUPER90 UI resolution; contact sheets are audit-only layouts."""
import json,hashlib,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
J=json.loads((R/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
W=copy.deepcopy(next(w for w in J['weapons'] if w['id']=='ue_super90'))
for slot,options in J['common_options'].items():
    ids={v['id'] for v in W['options'].get(slot,[])}
    for v in options:
        if v['id'] not in ids:W['options'].setdefault(slot,[]).append(v)
    if slot not in W['allowed']:W['allowed'].append(slot)
root=R/'Content/ColdSteelData/AttachmentIcons20260913';framed=root/'FramedFirearms'
rows=[]
def add(kind,slot,id,name,path):
    row=dict(index=len(rows)+1,kind=kind,slot=slot,id=id,name=name,path=str(path),key=path.stem,exists=path.exists())
    if path.exists():
        row['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as im:row['size']=list(im.size)
    rows.append(row)
for slot in J['slots']:
    if slot not in W['allowed'] or not any(v['id']!='false' for v in W['options'].get(slot,[])):continue
    common='category_'+slot;weapon='ue_super90_'+common
    directory=framed if (framed/(common+'.png')).exists() or (framed/(weapon+'.png')).exists() else root
    path=framed/(common+'.png') if (framed/(common+'.png')).exists() else directory/((weapon if (directory/(weapon+'.png')).exists() else common)+'.png')
    add('category',slot,'category',slot,path)
    for option in W['options'][slot]:
        id=option['id'];common=slot+'_'+id;weapon='ue_super90_'+common
        shared=id!='false' and (framed/(common+'.png')).exists()
        use_frame=shared or (framed/(weapon+'.png')).exists() or (not (root/(weapon+'.png')).exists() and (framed/(common+'.png')).exists())
        directory=framed if use_frame else root
        key=weapon if not shared and (directory/(weapon+'.png')).exists() else common
        add('option',slot,id,option['name'],directory/(key+'.png'))
baseline=O/'baseline.json'
if baseline.exists():raise RuntimeError('Do not overwrite a completed baseline')
baseline.write_text(json.dumps(dict(weapon=W,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
for page,start in enumerate(range(0,len(rows),12),1):
    sheet=Image.new('RGB',(1200,1120),(36,39,43));d=ImageDraw.Draw(sheet)
    for n,row in enumerate(rows[start:start+12]):
        x=(n%4)*300;y=(n//4)*370
        if row['exists']:
            src=Image.open(row['path']).convert('RGBA');large=src.copy();large.thumbnail((242,242));sheet.paste(large,(x+29,y+4),large)
            for size,offset in [(48,66),(64,134)]:
                thumb=src.resize((size,size),Image.Resampling.LANCZOS);sheet.paste(thumb,(x+offset,y+250),thumb)
        d.text((x+8,y+318),str(row['index'])+' '+row['name'],font=font,fill='white')
        d.text((x+8,y+340),row['slot']+'/'+row['id'],font=font,fill='#bfc5cf')
    sheet.save(O/('audit_before_'+str(page)+'.png'))
print(json.dumps(dict(categories=sum(r['kind']=='category' for r in rows),options=sum(r['kind']=='option' for r in rows),rows=[{k:r[k] for k in ('index','slot','id','key','exists')} for r in rows]),ensure_ascii=False,indent=2))
