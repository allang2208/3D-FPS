import ast,hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).parent;records={}
for root,names in [(R.parent/'stock5080-refined-v1',['m4-write','m4-load','akm-write','akm-load']),(R/'final-runtime',['m4-load','akm-load'])]:
 for name in names:
  p=root/(name+'.log');s=p.read_text(encoding='utf-8',errors='replace');m=re.search(r'STOCK_AUDIT: COMPLETE checks=(\d+) failures=(\d+)',s);assert m and int(m[2])==0 and 'STOCK_AUDIT: FAIL' not in s and 'Failed to compile Material' not in s
  records[root.name+'/'+name]={'checks':int(m[1]),'failures':int(m[2]),'log':str(p)}
for rifle in ['m4','akm']:
 folder=R/'final-runtime'/(rifle+'-load');frames=[];sheet=Image.new('RGB',(1280,820),(25,28,32));draw=ImageDraw.Draw(sheet)
 for row,stage in enumerate([10,11,13,14]):
  paths=sorted(folder.glob(f'reload-{stage:02d}-*.png'));assert paths
  for p in paths:
   im=Image.open(p).convert('RGB');im.thumbnail((800,450));frames.append(im)
  frames.extend([frames[-1]]*3)
  for col,f in enumerate([.1,.35,.6,.85]):
   p=paths[min(len(paths)-1,int((len(paths)-1)*f))];im=Image.open(p).convert('RGB').resize((320,180));sheet.paste(im,(col*320,row*205));draw.text((col*320+5,row*205+183),p.name,fill='white')
 frames[0].save(R/(rifle+'_reload_preview.gif'),save_all=True,append_images=frames[1:],duration=200,loop=0,optimize=False);sheet.save(R/(rifle+'_reload_contacts.jpg'),quality=92)
table=Image.new('RGB',(1280,1550),(33,36,41));d=ImageDraw.Draw(table)
for i,rifle in enumerate(['m4','akm']):
 im=Image.open(R/(rifle+'_detail.png')).convert('RGB').resize((1280,760));table.paste(im,(0,15+i*775));d.text((24,18+i*775),rifle.upper()+' / original receiver metal',fill='white')
table.save(R/'rifle_material_comparison.jpg',quality=95)
report={'stage':'5080 silhouette accepted; detail refinement integrated','runtime':records,'checks':sum(v['checks'] for v in records.values()),'failures':0,'final_asset_runtime_checks':sum(v['checks'] for k,v in records.items() if k.startswith('final-runtime/')),'source_topology':json.loads((R/'topology_uv_report.json').read_text()),'published_assets':json.loads((R/'publish_report.json').read_text()),'visual_evidence':'final-runtime and *_detail.png; latest revision inspected by assistant, final visual acceptance belongs to user','limits':['no packaged-build test','commandlet exits 1 for existing GameFeatureData configuration errors; Python import readback passed','native full-project build attempts encountered parallel UI/weather errors; this refinement uses the existing stock assembly entry']}
(R/'acceptance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
paths=[p for p in R.rglob('*') if p.is_file() and p.suffix.lower() in ['.fbx','.blend','.png','.jpg','.gif','.py'] and 'final-runtime' not in p.parts]
for p in R.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
(R/'asset_hashes.json').write_text(json.dumps({str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
print(json.dumps({'checks':report['checks'],'final_asset_runtime_checks':report['final_asset_runtime_checks'],'failures':0}),flush=True)
