"""Scoped merge of only the two repaired families after the asset save receipt."""
import json,sys,hashlib,copy,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TrouserFit20261018';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));from json_entries import replace
saved=json.loads((R/'saved_assets.json').read_text());inventory=json.loads((R/'fit_inventory.json').read_text());rows=[x for x in inventory['paths'] if x['action']=='tailored']
if not saved.get('completed') or len(saved.get('icons',{}))!=2:raise RuntimeError('Finish mesh and icon save before publication')
for file,sha in saved['source_sha256'].items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:raise RuntimeError('Unpublished changed source: '+file)
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[x.decode('utf-8-sig') for x in raw];catalog,config=[json.loads(t) for t in texts];updated={}
for item,label in [('ue_leather_pants','LeatherPants'),('ue_chainmail_pants','ChainmailPants')]:
    recipe=copy.deepcopy(config['items'][item]);remap={x['active_asset']:saved['meshes']['SK_'+Path(x['output']).stem] for x in rows if x['item']==item}
    def fitted(old):
        if old in remap:return remap[old]
        if old in remap.values():return old
        raise RuntimeError('Wearable changed during production: '+old)
    for rig,old in recipe['rig_meshes'].items():
        if rig=='Jason':recipe['rig_meshes'][rig]=fitted(old)
    for shoe,rigs in recipe.get('shoe_fit_meshes',{}).items():
        if 'Jason' in rigs:rigs['Jason']=fitted(rigs['Jason'])
    recipe['appearance_family']=label+'NativeWaist20261018';definition=copy.deepcopy(catalog[item]);definition.update(world_mesh=saved['meshes'][label+'_pickup'],ue_equipment_icon_mesh=saved['meshes'][label+'_icon'],ue_icon='Icons/TrouserFit20261018/'+item+'.png')
    texts[0]=replace(texts[0],[item],definition);texts[1]=replace(texts[1],['items',item],recipe);updated[item]=dict(definition=definition,recipe=recipe)
folder=D/'Icons/TrouserFit20261018';folder.mkdir(parents=True,exist_ok=True)
for item in updated:shutil.copy2(R/(item+'.png'),folder/(item+'.png'))
if any(path.read_bytes()!=before for path,before in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped merge; retry')
for path,before,text in zip(paths,raw,texts):
    backup=R/'Before'/path.name
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(before)
    path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,updated=updated,checked_items=6,checked_unique_paths=len(inventory['paths']),repaired_wearables=len(rows),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('TWO_TROUSER_FAMILIES_PUBLISHED',flush=True)
