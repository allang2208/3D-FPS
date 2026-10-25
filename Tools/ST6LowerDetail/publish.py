"""Publish ST6 lower detail assets, PNG icons and exact existing outfit pairings."""
import json,copy,hashlib,os,sys,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
KEYS=('ue_st6_tactical_pants','ue_st6_tactical_boots')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json');manifest=read(R/'manifest.json');mapping=manifest['path_map']
if not saved.get('completed'):raise RuntimeError('Finish all ST6 asset save batches before publication')
for row in manifest['meshes']:
    raw=(R/'Authored'/row['detail']).read_bytes() if row['detail'] else b''
    sha=hashlib.sha256(raw+json.dumps(saved['materials']).encode()).hexdigest()
    if saved['meshes'].get(row['source'],{}).get('detail_sha256')!=sha:raise RuntimeError('ST6 details changed after saving '+row['source'])
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];catalog,config=[json.loads(b.decode('utf-8-sig')) for b in raw]
baseline=read(R/'Inputs/modular_outfits.json')
for before,current in [(baseline['items'],config['items']),(baseline['body_variants']['kaitlin']['items'],config['body_variants']['kaitlin']['items'])]:
    for key in KEYS:
        for rig,source in before[key]['rig_meshes'].items():
            if current[key]['rig_meshes'].get(rig) not in (source,mapping[source]):raise RuntimeError('ST6 garment source changed concurrently: '+key+' '+rig)

def rewrite(v):
    if isinstance(v,str):return mapping.get(v,v)
    if isinstance(v,list):return [rewrite(x) for x in v]
    if not isinstance(v,dict):return v
    out={k:rewrite(x) for k,x in v.items()}
    for k,x in list(out.items()):
        if k in mapping:
            target=mapping[k]
            if target in out and out[target]!=x:raise RuntimeError('Conflicting outfit pairing '+target)
            out[target]=copy.deepcopy(x)
    return out
candidate=rewrite(config)
for items in (candidate['items'],candidate['body_variants']['kaitlin']['items']):
    for key in KEYS:items[key]['appearance_family']='ST6LowerDetail20261024'
catalog_out=raw[0].decode('utf-8-sig');updated={}
descriptions={
 'ue_st6_tactical_pants':'深灰防撕裂战术长裤，配立体腿袋、翻盖扣件、加固套结线和分区护膝。黑色弹力裁片与卡其包边延续 ST6 套装风格。',
 'ue_st6_tactical_boots':'卡其皮革与深灰织物拼接战术靴，带弧形针脚、加固鞋舌、金属鞋眼及绳端套，分层橡胶沿条与防滑齿纹鞋底。'}
for key in KEYS:
    item=copy.deepcopy(catalog[key]);item.update(ue_icon='Icons/ST6LowerDetail20261024/'+key+'.png',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=0,ue_icon_roll=0,world_mesh=saved['pickups'][key],world_material='',desc=descriptions[key]);updated[key]=item
    catalog_out=entries.replace(catalog_out,[key],item)
config_out=raw[1].decode('utf-8-sig');changed=[]
for prefix,olditems,newitems in [(['items'],config['items'],candidate['items']),(['body_variants','kaitlin','items'],config['body_variants']['kaitlin']['items'],candidate['body_variants']['kaitlin']['items'])]:
    for key,new in newitems.items():
        if new!=olditems[key]:config_out=entries.replace(config_out,prefix+[key],new);changed.append(prefix+[key])
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Shared outfit/catalog changed; reread and merge before publication')
for key in KEYS:
    for destination in (D/'Icons/ST6LowerDetail20261024'/(key+'.png'),D/'Icons'/(key+'.png'),D/'Icons/ST6LowerSet20261018'/(key+'.png')):
        backup=R/'Before'/('_'.join(destination.relative_to(P).parts))
        if destination.exists() and not backup.exists():shutil.copy2(destination,backup)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(key+'.png'),destination)
for path,before,text in zip(paths,raw,(catalog_out,config_out)):
    backup=R/'Before'/path.name
    if not backup.exists():backup.write_bytes(before)
    temp=path.with_name(path.name+'.st6-detail.tmp');temp.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    if path.read_bytes()!=before:raise RuntimeError('Concurrent writer at '+str(path))
    os.replace(temp,path)
(R/'published.json').write_text(json.dumps(dict(completed=True,items=updated,mesh_path_map=mapping,changed_config_items=changed,legacy_pairing_keys_retained=True,original_attributes_preserved=True,runtime_tested=False,git_commit=None,git_push=None),ensure_ascii=False,indent=2),encoding='utf-8')
print('ST6_LOWER_DETAIL_PUBLISHED',len(mapping),'mesh routes; PNG inventory for both items',flush=True)
