"""Publish only this helmet's head attachments, icon and pickup references."""
import json,hashlib,runpy,shutil,os,uuid,sys
from pathlib import Path
from datetime import datetime
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'HelmetDetailR1';D=P/'Content/ColdSteelData';KEY='ue_modern_tactical_helmet'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
saved=read(R/'saved.json');art=read(R/'artwork.json');before=read(R/'before.json')
if not saved['completed']:raise RuntimeError('Helmet asset save is incomplete')
for key,file in [('Jason',R/'Authored/helmet_Jason_wear.json'),('Kaitlin',R/'Authored/helmet_Kaitlin_wear.json'),('pickup',Path(art['pickup'])),('display',Path(art['icon']['display']))]:
    if saved['meshes'][key]['sha256']!=sha(file):raise RuntimeError('Helmet source changed after save: '+key)
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'];path=D/'player_body.json';raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'));owned=[]
for rig,fields in [('Jason',['head_equipment',KEY]),('Kaitlin',['body_variants','kaitlin','head_equipment',KEY])]:
    obj=data
    for part in fields:obj=obj[part]
    old=before['head_equipment'][rig]['static_mesh'];new=saved['meshes'][rig]['asset']
    if obj['static_mesh'] not in [old,new]:raise RuntimeError('Concurrent helmet attachment change: '+rig)
    obj['static_mesh']=new;owned.append(tuple(fields+['static_mesh']))
body_receipt=commit(path,raw,data,owned_paths=owned,producer=__file__)
path=D/'items.json';raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'));item=data[KEY];owned=[]
updates={'world_mesh':saved['meshes']['pickup']['asset'],'ue_equipment_icon_mesh':saved['meshes']['display']['asset'],'desc':'土棕色高切战术头盔，采用细颗粒复合壳体、连续橡胶盔缘、开槽侧导轨和三点前支座。内置缓冲垫、四点下颏带与后部调节旋钮。'}
for field,value in updates.items():
    if field!='desc' and item[field] not in [before['item'][field],value]:raise RuntimeError('Concurrent helmet catalog change: '+field)
    item[field]=value;owned.append((KEY,field))
text=raw.decode('utf-8-sig')
for field,value in updates.items():text=entries.replace(text,[KEY,field],value)
result=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
(R/'items-before.json').write_bytes(raw)
temp=path.with_name('.items-helmet1-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(result)
if path.read_bytes()!=raw:
    temp.unlink();raise RuntimeError('Catalog changed during helmet publication; reload before merging')
os.replace(temp,path)
catalog_receipt=dict(status='applied',owned_paths=owned,before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=hashlib.sha256(result).hexdigest(),local_config_applied=True)
for dest in [D/item['ue_icon'],D/'Icons'/(KEY+'.png')]:
    dest.parent.mkdir(parents=True,exist_ok=True);backup=R/'BeforeIcons'/dest.parent.name/dest.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
    temp=dest.with_name(dest.name+'.helmet1-'+uuid.uuid4().hex+'.tmp');shutil.copy2(art['icon']['png'],temp);os.replace(temp,dest)
record=dict(completed=True,completed_at=datetime.now().astimezone().isoformat(),item=KEY,head_variants=['Jason','Kaitlin'],meshes=saved['meshes'],materials=len(saved['materials']),icon=saved['icon'],body_config=body_receipt,catalog=catalog_receipt,gameplay_tested=False,inventory_regrant=False)
(R/'published.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('HELMET_DETAIL_PUBLISHED',flush=True)
