"""Publish saved V9 models, icons and Thor-only exclusions, preserving other weapons."""
from pathlib import Path
import json,datetime,shutil,os
P=Path(__file__).resolve().parent;R=P.parents[2]
models=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
icons=json.loads((P/'icon_import_receipt.json').read_text(encoding='utf-8'))
if not models['complete'] or not icons['complete']:raise RuntimeError('Assets are not all saved')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
rows={r['id']:r for r in manifest['parts']};paths={r['id']:r['mesh'] for r in models['models']}
retired=['ancient_breaking_seal_seat','storm_drive_seat']
backup=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
changes=[]
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
 path=R/'Content/ColdSteelData'/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
 if 'modules' in file:
  seats=data['slots']['head_mount'];before={key:seats.get(key) for key in [*rows,*retired]}
  for key,row in rows.items():seats[key].update(mesh=paths[key],model_revision='SeatDistinctV9',appearance=row['appearance'],design_reference='SeatDistinctV9/ThunderSeats_DistinctV9.blend')
  for key in retired:seats.pop(key,None)
  after={key:seats.get(key) for key in [*rows,*retired]}
 else:
  column=next(c for c in data['columns'] if c['key']=='head_mount');before=json.loads(json.dumps(column))
  column['excluded_options']=list(dict.fromkeys(column.get('excluded_options',[])+retired))
  for option in column['options']:
   key=option['id']
   if key not in rows:continue
   option['appearance']=rows[key]['appearance']
   option['description']=('雷神之锤专属。厚实的闭合嵌银回环护住原厂雷纹圆徽，回折锻肩承接飞锤往复，将蓄满重击化为可召回的旋转飞锤。' if key=='guan_lei_seat' else '雷神之锤专属。三尖锻造引雷冠向上收束，嵌银雷纹沿内收锻肩汇入原厂圆徽；单手举锤蓄力，指向地面召下疾雷。')
  after=column
 if path.read_bytes()!=raw:raise RuntimeError('Concurrent edit: '+file)
 shutil.copy2(path,backup/file);tmp=path.with_name(file+'.seat-v9-pending');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)
 changes.append(dict(file=str(path),before=before,after=after,backup=str(backup/file)))
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,changes=changes,retired_only_from='ue_thunder_god_hammer',retired=retired,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('THUNDER_DISTINCT_V9_PUBLISHED')
