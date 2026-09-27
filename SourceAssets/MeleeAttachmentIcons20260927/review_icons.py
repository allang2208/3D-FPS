"""Audit requested icon set and create visual review sheets; no gameplay test."""
from pathlib import Path
import json,hashlib,collections
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
base=json.loads((P/'baseline.json').read_text(encoding='utf-8'))
receipts={}
for path in P.glob('render_*.json'):
 if path.stem.endswith('_sample'):continue
 for row in json.loads(path.read_text(encoding='utf-8')):receipts[row['key']]=row
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
rows=[];issues=[]
for original in base['icons']:
 row=dict(original);key=row['key'];r=receipts.get(key)
 if not r:
  issues.append(key+': no production receipt');continue
 file=Path(row['resolved']) if r['action']=='retain' else P/'Icons'/(key+'.png')
 if not file.exists():issues.append(key+': missing output');continue
 im=Image.open(file);a=im.getchannel('A');bbox=a.getbbox()
 fill=max(bbox[2]-bbox[0],bbox[3]-bbox[1])/1024 if bbox else 0
 if im.size!=(1024,1024) or im.mode!='RGBA':issues.append(key+': must be 1024 RGBA')
 if not bbox or a.getextrema()!=(0,255):issues.append(key+': invalid transparent background')
 if not .79<=fill<=.87:issues.append(key+': framing '+str(fill))
 if bbox and (bbox[0]<12 or bbox[1]<12 or bbox[2]>1012 or bbox[3]>1012):issues.append(key+': clipping risk')
 row.update(output=str(file),output_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
  action='retain' if r['action']=='retain' else 'replace' if row['resolved'] else 'add',
  alpha_bounds=bbox,fill=fill,production=r)
 rows.append(row)
for wid in dict.fromkeys(r['weapon'] for r in rows):
 subset=[r for r in rows if r['weapon']==wid]
 sheet=Image.new('RGB',(1500,230*((len(subset)+5)//6)),(35,38,42));d=ImageDraw.Draw(sheet)
 for n,r in enumerate(subset):
  x=n%6*250;y=n//6*230
  d.rectangle((x+2,y+2,x+247,y+228),outline=(85,90,96))
  im=Image.open(r['output']).convert('RGBA');im.thumbnail((222,166),Image.Resampling.LANCZOS)
  sheet.paste(im,(x+125-im.width//2,y+7+(166-im.height)//2),im)
  d.text((x+8,y+174),r['name'],font=font,fill=(235,235,235))
  d.text((x+8,y+199),r['slot']+' / '+r['id'],font=small,fill=(160,175,190))
 sheet.save(P/('after_'+wid+'.jpg'),quality=95)
summary={'requested':len(base['icons']),'completed':len(rows),
 'actions':dict(collections.Counter(r['action'] for r in rows)),'issues':issues}
(P/'audit.json').write_text(json.dumps(dict(summary,icons=rows),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
