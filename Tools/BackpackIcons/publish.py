"""Publish the completed canonical UE catalog render, including legacy PNG paths."""
import argparse,hashlib,json,os,shutil,struct,tempfile
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackIcons20261025/FrontR1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
a=argparse.ArgumentParser();a.add_argument('--definitions',default='');a.add_argument('--directory',default=str(R/'Catalog'));args=a.parse_args()
plan=read(R/'plan.json');defs=args.definitions.split(',') if args.definitions else [r['id'] for r in plan['items']]
folder=Path(args.directory);author=read(folder/'author-receipt.json')
if author['exit_code']!=0 or not set(defs)<=set(author['definitions']):raise RuntimeError('Finish the selected UE catalog export first')
body=read(P/'Content/ColdSteelData/player_body.json');items=read(P/'Content/ColdSteelData/items.json');rows=[]
for row in plan['items']:
 key=row['id']
 if key not in defs:continue
 item=items[key];outfit=body['outfits'][key]
 selected=item.get('ue_equipment_icon_mesh') or outfit.get('inventory_static_mesh') or outfit['world_static_mesh']
 if selected!=row.get('display_asset',row['source']):raise RuntimeError('The display source changed during authoring: '+key)
 image=folder/(key+'.png');raw=image.read_bytes();size=struct.unpack('>II',raw[16:24]);expected=(round(320*item['grid_w']/item['grid_h']),320)
 if raw[:8]!=b'\x89PNG\r\n\x1a\n' or size!=expected:raise RuntimeError('Incomplete catalog image: '+key)
 paths={P/'Content/ColdSteelData/Icons'/(key+'.png'),P/'Content/ColdSteelData'/item['ue_icon']}
 for target in paths:
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.backpack-icon-',suffix='.tmp',delete=False) as stream:
   temp=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
  os.replace(temp,target)
 rows.append(dict(id=key,display_mesh=selected,rotation=[0,-90,0],projection='orthographic_front',dimensions=list(size),sha256=hashlib.sha256(raw).hexdigest(),targets=[str(p) for p in paths]))
receipt=R/'published.json';result=read(receipt) if receipt.exists() else dict(revision=plan['revision'],items=[])
result['items']=[r for r in result['items'] if r['id'] not in defs]+rows
result.update(completed=len(result['items'])==len(plan['items']),gameplay_tested=False,player_saves_modified=False,render_log=author['log'])
receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('BACKPACK_FRONT_PNG_PUBLISHED',len(rows),flush=True)
