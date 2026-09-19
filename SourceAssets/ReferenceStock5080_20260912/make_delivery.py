import json,re,hashlib,ast
from pathlib import Path
from PIL import Image,ImageDraw
P=Path(__file__).parent;run=P/'stock5080-v1';results={}
for rifle in ['m4','akm']:
 for phase in ['write','load']:
  name=rifle+'-'+phase;text=(run/(name+'.log')).read_text(encoding='utf-8',errors='replace');match=re.search(r'STOCK_AUDIT: COMPLETE checks=(\d+) failures=(\d+)',text)
  assert match and int(match[2])==0 and 'STOCK_AUDIT: FAIL' not in text,name
  results[name]={'checks':int(match[1]),'failures':int(match[2]),'log':str((run/(name+'.log')).relative_to(P))}
 frames=[];sheet=Image.new('RGB',(1280,4*205),(25,28,32));draw=ImageDraw.Draw(sheet)
 for row,stage in enumerate([10,11,13,14]):
  paths=sorted((run/(rifle+'-write')).glob(f'reload-{stage:02d}-*.png'));assert paths
  for p in paths:
   im=Image.open(p).convert('RGB');im.thumbnail((800,450));frames.append(im)
  frames.extend([frames[-1]]*3)
  for col,fraction in enumerate([.1,.35,.6,.85]):
   path=paths[min(len(paths)-1,int((len(paths)-1)*fraction))];im=Image.open(path).convert('RGB').resize((320,180));sheet.paste(im,(col*320,row*205));draw.text((col*320+5,row*205+183),path.name,fill='white')
 frames[0].save(P/(rifle+'_reload_preview.gif'),save_all=True,append_images=frames[1:],duration=200,loop=0,optimize=False)
 sheet.save(P/(rifle+'_reload_contacts.jpg'),quality=92)
report={'generation':'RTX 5080 TRELLIS.2 1024_cascade multiview','generation_seconds':257.52,'runtime':results,'checks':sum(r['checks'] for r in results.values()),'failures':0,'visual_status':'inspected by assistant; user has not accepted this revision','known_limitations':['generated surface edge waviness and nonmanifold remnants','commandlet exit 1 with pre-existing GameFeatureData errors','not packaged','silent preview only']}
(P/'acceptance.json').write_text(json.dumps(report,indent=2))
hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file() and (f.suffix.lower() in ['.glb','.fbx','.blend','.png'] and ('stock5080-v1' not in f.parts))}
(P/'asset_hashes.json').write_text(json.dumps(hashes,indent=2))
for f in P.glob('*.py'):ast.parse(f.read_text(encoding='utf-8-sig'))
print(json.dumps(report),flush=True)
