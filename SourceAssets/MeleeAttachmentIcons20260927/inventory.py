"""Snapshot all visible melee/tool attachment and category icons before replacement."""
from pathlib import Path
import json, hashlib, shutil
from PIL import Image, ImageDraw, ImageFont

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
ICONS=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
BASE=P/'Before'
BASE.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
rows=[]
catalogs={}
for file in ['melee-gunsmith.json','tool-gunsmith.json']:
    path=ROOT/'Content/ColdSteelData'/file
    catalog=json.loads(path.read_text(encoding='utf-8-sig'))
    catalogs[file]=catalog
    for weapon in catalog['weapons']:
        wid=weapon['id']
        for col in catalog['columns']:
            slot=col['key']
            options=[{'id':'false','name':col['default']}]+col.get('options',[])
            for opt in [{'id':'category','name':col['name']}]+options:
                if opt.get('weapons') and wid not in opt['weapons']:continue
                oid=opt['id']
                key=f'{wid}_category_{slot}' if oid=='category' else f'{wid}_{slot}_{oid}'
                common=f'category_{slot}' if oid=='category' else f'{slot}_{oid}'
                resolved=ICONS/(key+'.png')
                if not resolved.exists():resolved=ICONS/(common+'.png')
                row={'weapon':wid,'slot':slot,'id':oid,'name':opt['name'],'key':key,
                     'catalog':file,'resolved':str(resolved) if resolved.exists() else None}
                if resolved.exists():
                    raw=resolved.read_bytes()
                    row['sha256']=hashlib.sha256(raw).hexdigest()
                    dest=BASE/resolved.name
                    if not dest.exists():shutil.copy2(resolved,dest)
                    im=Image.open(resolved).convert('RGBA')
                    alpha=im.getchannel('A')
                    row.update(size=list(im.size),bbox=alpha.getbbox(),alpha_extrema=list(alpha.getextrema()))
                rows.append(row)
if (P/'baseline.json').exists():raise RuntimeError('Baseline already exists; do not overwrite an earlier audit.')
(P/'baseline.json').write_text(json.dumps({'catalogs':catalogs,'icons':rows},ensure_ascii=False,indent=2),encoding='utf-8')
for wid in dict.fromkeys(r['weapon'] for r in rows):
    subset=[r for r in rows if r['weapon']==wid]
    sheet=Image.new('RGB',(1500,230*((len(subset)+5)//6)),(35,38,42))
    d=ImageDraw.Draw(sheet)
    for n,r in enumerate(subset):
        x=(n%6)*250;y=(n//6)*230
        d.rectangle((x+2,y+2,x+247,y+228),outline=(85,90,96))
        if r['resolved']:
            im=Image.open(r['resolved']).convert('RGBA');im.thumbnail((222,166),Image.Resampling.LANCZOS)
            sheet.paste(im,(x+125-im.width//2,y+7+(166-im.height)//2),im)
        else:d.text((x+75,y+72),'MISSING',font=font,fill=(255,90,80))
        d.text((x+8,y+174),r['name'],font=font,fill=(235,235,235))
        d.text((x+8,y+199),r['slot']+' / '+r['id'],font=small,fill=(160,175,190))
    sheet.save(P/('before_'+wid+'.jpg'),quality=95)
print(json.dumps({'weapons':list(dict.fromkeys(r['weapon'] for r in rows)),'entries':len(rows),
    'resolved_files':len(set(r['resolved'] for r in rows if r['resolved'])),
    'missing':sum(r['resolved'] is None for r in rows)},ensure_ascii=False))
