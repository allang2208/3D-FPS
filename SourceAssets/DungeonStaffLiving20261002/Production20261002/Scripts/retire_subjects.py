"""Archive staff-only sample maps after actual production save and native build."""
import json,hashlib,shutil,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];STAFF=ROOT.parent;PROJECT=STAFF.parents[1]
receipt=ROOT/'Receipts/install.json';saved=json.loads(receipt.read_text('utf8'))
build=json.loads((ROOT/'Receipts/native-build.json').read_text('utf-8-sig'))
if saved.get('stage')!='map_saved' or build.get('editor_exit')!=0 or build.get('game_exit')!=0:
    raise RuntimeError('Keep staff samples until production integration actually completes')
archive=(PROJECT/'trash/staff-living-subjects-retired-20261002').resolve();archive.mkdir(parents=True,exist_ok=True)
cp=STAFF/'Config/room.json';cfg=json.loads(cp.read_text('utf8'))
targets=list(cfg.get('maps',{}).values())+[cfg.get('sample_map')]
entries=[]
prior=archive/'manifest.json'
if prior.exists():entries=json.loads(prior.read_text('utf8'))['files']
for target in targets:
    if not target:continue
    disk=(PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap')).resolve()
    if not disk.is_relative_to((PROJECT/'Content/GameMaps/Design').resolve()):raise RuntimeError('Unexpected sample archive scope')
    if not disk.exists():continue
    dest=(archive/'Maps'/disk.name).resolve()
    if not dest.is_relative_to(archive):raise RuntimeError('Unexpected archive destination')
    dest.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(disk.read_bytes()).hexdigest()
    if dest.exists():raise RuntimeError('Preserve existing recovery map '+str(dest))
    size=disk.stat().st_size;shutil.move(str(disk),str(dest))
    entries.append(dict(original=str(disk),archive=str(dest),size=size,sha256=digest,reason='User accepted staff theme; production modules saved',replacement=cfg['production_map']))
    prior.write_text(json.dumps(dict(files=entries,retired_at=datetime.datetime.now().isoformat(),shared_assets_retained=True),ensure_ascii=False,indent=2),encoding='utf8')
cfg['retired_subject_maps']=[p for p in targets if p];cfg.pop('maps',None);cfg.pop('sample_map',None)
cfg['sample_maps_retired']=True;cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
saved['samples_retirement']='archived';saved['retirement_manifest']=str(prior)
receipt.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_SUBJECT_MAPS_ARCHIVED',len(entries))
