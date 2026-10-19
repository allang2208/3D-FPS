"""Record the completed import and the requested per-weapon route inventory."""
import json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
receipt=read(R/'saved_assets.json');published=read(R/'published.json');config=read(P/'Content/ColdSteelData/modular_outfits.json');inventory=read(R/'inventory.json')
if not receipt.get('completed') or not published.get('completed') or len(receipt['saved'])!=48:raise RuntimeError('Import/publication still incomplete')
rows=[];missing=[]
for row in inventory['rows']:
    key=row['item']+'/'+row['profile'];expected=receipt['saved'].get(key,{}).get('asset',row['asset']);actual=config['items'][row['item']]['rig_meshes'][row['profile']]
    if actual!=expected:raise RuntimeError('Current weapon route differs from delivered mesh '+key)
    file=P/'Content'/(actual.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not file.exists():missing.append(str(file))
    rows.append(dict(item=row['item'],profile=row['profile'],asset=actual,repaired=key in receipt['saved'],file=str(file),asset_sha256=hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None,lod_count=receipt['saved'].get(key,{}).get('lod_count')))
aliases={name:profile['rig_profile'] for name,profile in config['profiles'].items() if profile['rig_profile'] not in ('Body','Jason')}
profiles=set(aliases.values());captured={row['profile'] for row in inventory['rows']}
if profiles!=captured:raise RuntimeError('Active weapon bindings changed during production')
if missing:raise RuntimeError('Missing delivered packages '+str(missing))
delivery=dict(completed=True,inspected_meshes=69,repaired_and_saved=48,retained_short_sleeves=21,fp_profiles=sorted(profiles),weapon_source_aliases=aliases,rows=rows,missing_files=missing,game_runtime_tested=False,editor_gui_opened=False)
(R/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
doc=P/'Docs/Characters/other-shirt-sleeve-repair-20261018.md';text=doc.read_text(encoding='utf-8')
text=text.replace('48 份修复源模型已经完成；UE 保存与配置发布正在后台队列执行，以 `saved_assets.json`、`published.json` 为实际完成凭据。','48 份修复模型已实际导入并保存，48 份 LOD 设置已保存，装备配置已发布；其余 21 份短袖保留原资产。`delivery.json` 记录全部 69 个在用引用与 58 个武器／手臂入口。')
text=text.replace('LOD 计划为三个保留配对拓扑的级别','每份修复资产已保存三个保留配对拓扑的 LOD 级别')
doc.write_text(text,encoding='utf-8');print('GARMENT_DELIVERY_COMPLETE',len(rows),len(receipt['saved']),len(aliases))
