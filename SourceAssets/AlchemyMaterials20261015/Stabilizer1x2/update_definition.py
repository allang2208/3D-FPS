from pathlib import Path
import json,sys,shutil
ROOT=Path(__file__).resolve().parent;ASSETS=ROOT.parent;PROJECT=ASSETS.parents[1]
ID='alchemy_compound_stabilizer'
def load(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,obj):
 b=ROOT/'Before'/p.relative_to(PROJECT);b.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and not b.exists():shutil.copy2(p,b)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n','utf8')
if sys.argv[-1]=='prepare':
 for name in ('model_manifest.json','texture_manifest.json'):
  p=ASSETS/name;d=load(p);d['assets']['Stabilizer']['grid']=[1,2];write(p,d)
else:
 p=PROJECT/'Content/ColdSteelData/items.json';raw=p.read_text('utf-8-sig');d=json.loads(raw)
 old=json.dumps({ID:d[ID]},ensure_ascii=False,indent=2)[1:-1].strip('\n')
 d[ID]['grid_w']=1;d[ID]['grid_h']=2
 new=json.dumps({ID:d[ID]},ensure_ascii=False,indent=2)[1:-1].strip('\n')
 if old not in raw:raise RuntimeError('Preserve changed item formatting')
 p.write_text(raw.replace(old,new,1),'utf8')
 p=ASSETS/'Receipts/data-installation.json';receipt=load(p);receipt['items'][ID]=d[ID];write(p,receipt)
 p=ASSETS/'presentation.json';presentation=load(p)
 for icon in presentation['icons']:
  if icon['id']==ID:icon['inventory_registered']=True
 write(p,presentation)
 print('STABILIZER_GRID_UPDATED 1x2')
