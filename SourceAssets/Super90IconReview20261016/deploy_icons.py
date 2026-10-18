"""Publish reviewed images, retaining exact-path backups and authoring entrypoints."""
import json,shutil,hashlib
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent;D=R/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
B=R/'trash/super90-icons-replaced-20261016'
data=json.loads((O/'generation_manifest.json').read_text(encoding='utf-8'));baseline=json.loads((O/'baseline.json').read_text(encoding='utf-8'))
if (O/'deployment.json').exists():raise RuntimeError('This deployment is already recorded; do not overwrite history')
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={r['key']:r['sha256'] for r in baseline['rows'] if r['exists']}
entries=[dict(name=e['name'],key=e['key'],source=Path(e['generated_file']),method='imagegen from actual model') for e in data['entries']]
entries.extend([
 dict(name='manual_loading',key='ue_super90_reload_device_false',source=D/'tactical_false.png',method='shared neutral no-loader symbol'),
 dict(name='tactical_vertical',key='underbarrel_tactical_vertical_foregrip',source=D/'ue_m4a1_underbarrel_tactical_vertical_foregrip.png',method='promote existing same donor part to common key; Super90 models.json points to this M4 donor'),
 dict(name='magazine_category',key='category_magazine',source=D/'magazine_ext_mag.png',method='shared representative magazine without state badge')])
for e in entries:
    target=D/(e['key']+'.png')
    if target.exists() and (e['key'] not in before or hashfile(target)!=before[e['key']]):raise RuntimeError('Target changed since baseline: '+str(target))
backups=[]
def backup(path):
    if not path.exists():return
    dest=B/path.relative_to(R)
    if dest.exists():raise RuntimeError('Existing backup: '+str(dest))
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    backups.append(dict(original=str(path.relative_to(R)),backup=str(dest.relative_to(R)),sha256=hashfile(path),bytes=path.stat().st_size))
(O/'Generated').mkdir(exist_ok=True)
saved=[]
for e in entries:
    master=O/'Generated'/(e['name']+'.png');shutil.copy2(e['source'],master)
    target=D/(e['key']+'.png');package=target.with_suffix('.uasset')
    old_package=hashfile(package) if package.exists() else None
    backup(target);backup(package);shutil.copy2(master,target)
    saved.append(dict(key=e['key'],source=str(master.relative_to(R)),runtime_png=str(target.relative_to(R)),sha256=hashfile(target),previous_package_sha256=old_package,method=e['method']))
for folder,key,name in [('Super90CommonStocks20261013','ue_super90_stock_false','stock'),('Super90RearGrips20261012','ue_super90_reargrip_false','reargrip')]:
    source=R/'SourceAssets'/folder
    for path in [source/(key+'.png'),source/'author_factory_icon.py']:backup(path)
    shutil.copy2(O/'Generated'/(name+'.png'),source/(key+'.png'))
    (source/'author_factory_icon.py').write_text('"""Restore the reviewed 2026-10-16 imagegen master; see Super90IconReview20261016."""\nfrom pathlib import Path\nimport shutil\nO=Path(__file__).parent\nshutil.copy2(O.parent/"Super90IconReview20261016/Generated/'+name+'.png",O/"'+key+'.png")\nprint("SUPER90_FACTORY_ICON_RESTORED")\n',encoding='utf-8')
report=dict(entries=saved,backups=backups,cpp_changed=False,game_tested=False,counts=dict(categories=8,options=36,changed_display_entries=9,retained_display_entries=35))
(O/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'manifest.json').write_text(json.dumps(backups,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SUPER90_PNGS_SAVED',len(saved),'BACKUPS',len(backups))
