"""Install the new helmet packages and merge just its display references."""
import hashlib,json,os,runpy,shutil,sys,uuid
from pathlib import Path
P=Path(__file__).resolve().parents[2]
REV=globals().get('HELMET_REVISION','HelmetContourR2')
PREVIOUS_WEAR=globals().get('PREVIOUS_HELMET_WEAR','HelmetHairFitR1')
PREVIOUS_DISPLAY=globals().get('PREVIOUS_HELMET_DISPLAY','HelmetDetailR1')
R=P/'SourceAssets/ModernTacticalSet20261113'/REV
DATA=P/'Content/ColdSteelData'
REL=Path('Characters/ModularOutfit20260924/ModernTacticalSet20261113')/REV
KEY='ue_modern_tactical_helmet'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_exact(path,data,expected):
    temp=path.with_name(path.name+'.helmet-contour-'+uuid.uuid4().hex+'.tmp')
    temp.write_bytes(data)
    try:
        if path.read_bytes()!=expected:raise RuntimeError('Concurrent change to '+str(path))
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()
def install(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        if sha(src)!=sha(dst):raise RuntimeError('New helmet package already occupied: '+str(dst))
    else:
        temp=dst.with_name(dst.name+'.helmet-contour-'+uuid.uuid4().hex+'.tmp')
        try:
            shutil.copyfile(src,temp);os.rename(temp,dst)
        finally:
            if temp.exists():temp.unlink()
read=lambda p:json.loads(p.read_bytes())
saved=read(R/'saved.json');art=read(R/'artwork.json')
if not saved['completed']:raise RuntimeError('Finish saving first')
files={'Jason':R/'Authored/helmet_Jason_wear.json','Kaitlin':R/'Authored/helmet_Kaitlin_wear.json','pickup':Path(art['pickup']),'display':Path(art['icon']['display'])}
for k,p in files.items():
    if sha(p)!=saved['meshes'][k]['source_sha']:raise RuntimeError('Authored mesh changed: '+k)
stage=R/'StageHost/Content';new_packages=[]
for item in [row['asset'] for row in saved['meshes'].values()]+[saved['icon']]:
    rel=Path(item.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not rel.is_relative_to(REL):raise RuntimeError('Asset outside helmet revision')
    for ext in ('.uasset','.uexp','.ubulk'):
        src=(stage/rel).with_suffix(ext)
        if ext=='.uasset' and not src.exists():raise RuntimeError('Missing '+str(src))
        if src.is_file():install(src,(P/'Content'/rel).with_suffix(ext));new_packages.append(str(rel.with_suffix(ext)))
path=DATA/'player_body.json';raw=path.read_bytes();cfg=json.loads(raw);owned=[]
for rig,keys in [('Jason',('head_equipment',KEY)),('Kaitlin',('body_variants','kaitlin','head_equipment',KEY))]:
    obj=cfg
    for name in keys:obj=obj[name]
    new=saved['meshes'][rig]['asset']
    if obj['static_mesh'] not in (new,new.replace('/'+REV+'/','/'+PREVIOUS_WEAR+'/')):raise RuntimeError('Concurrent helmet edit: '+rig)
    obj['static_mesh']=new;owned.append(keys+('static_mesh',))
receipt=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](path,raw,cfg,owned_paths=owned,producer=__file__)
path=DATA/'items.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');item=json.loads(raw)[KEY]
for field,role in [('world_mesh','pickup'),('ue_equipment_icon_mesh','display')]:
    new=saved['meshes'][role]['asset']
    if item[field] not in (new,new.replace('/'+REV+'/','/'+PREVIOUS_DISPLAY+'/')):raise RuntimeError('Concurrent item appearance edit: '+field)
    text=json_entries.replace(text,[KEY,field],new)
result=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf8')
if result!=raw:write_exact(path,result,raw)
for target in [DATA/item['ue_icon'],DATA/'Icons'/(KEY+'.png')]:
    new=Path(art['icon']['png']).read_bytes();before=target.read_bytes()
    if new!=before:
        backup=R/'BeforeIcons'/target.parent.name/target.name;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(before)
        write_exact(target,new,before)
(R/'published.json').write_text(json.dumps(dict(completed=True,packages=new_packages,body=receipt,item_fields=['world_mesh','ue_equipment_icon_mesh'],png=item['ue_icon'],gameplay_tested=False),indent=2),encoding='utf8')
print('HELMET_CONTOUR_INSTALLED',len(new_packages),flush=True)
