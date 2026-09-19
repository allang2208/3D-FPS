import unreal,json,hashlib,shutil,uuid
from pathlib import Path
O=Path(__file__).parent;root=O.parents[1];saves=root/'Saved/SaveGames'
report=O/'player_akm_grant.json'
assert not report.exists(), 'This one-time grant has already run'
valid=[]
for suffix in ['A','B']:
    slot='ColdSteelPlayer_'+suffix;p=saves/(slot+'.sav')
    if p.exists() and hashlib.sha1(p.read_bytes()).hexdigest().upper()==(saves/(slot+'.sha1')).read_text(encoding='utf-8-sig').strip():
        obj=unreal.GameplayStatics.load_game_from_slot(slot,0)
        if obj:valid.append((obj.get_editor_property('profile').get_editor_property('generation'),obj))
assert valid,'No valid player save'
gen,obj=max(valid,key=lambda x:x[0]);profile=obj.get_editor_property('profile');items=list(profile.get_editor_property('items'))
get=lambda i,k:i.get_editor_property(k)
occupied=set()
for i in items:
    if get(i,'place')==0:
        occupied.update(get(i,'cell')+y*18+x for y in range(get(i,'height')) for x in range(get(i,'width')))
cell=next((c for c in range(72) if c%18+5<=18 and c//18+2<=4 and not any(c+y*18+x in occupied for y in range(2) for x in range(5))),None)
assert cell is not None,'No free 5x2 backpack space'
backup=O/'PlayerSaveBeforeAKM';backup.mkdir(exist_ok=False)
for p in saves.glob('ColdSteelPlayer_*'):
    if p.suffix in ['.sav','.sha1']:shutil.copy2(p,backup/p.name)
item=unreal.ColdSteelItem();iid=uuid.uuid4().hex
data=json.loads((root/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))['ue_akm']
for k,v in dict(instance_id=iid,definition='ue_akm',data=json.dumps(data,ensure_ascii=False,separators=(',',':')),count=1,stack_max=1,width=5,height=2,place=0,cell=cell,backpack_cell=-1,magazine=30,reserve=90).items():item.set_editor_property(k,v)
before=[i.export_text() for i in items];items.append(item);profile.set_editor_property('items',items);profile.set_editor_property('generation',gen+1);obj.set_editor_property('profile',profile)
slot='ColdSteelPlayer_'+('A' if (gen+1)%2 else 'B')
assert unreal.GameplayStatics.save_game_to_slot(obj,slot,0)
p=saves/(slot+'.sav');(saves/(slot+'.sha1')).write_text(hashlib.sha1(p.read_bytes()).hexdigest().upper(),encoding='ascii')
check=unreal.GameplayStatics.load_game_from_slot(slot,0).get_editor_property('profile');after=list(check.get_editor_property('items'))
assert [i.export_text() for i in after[:-1]]==before
assert get(after[-1],'instance_id')==iid and get(after[-1],'place')==0 and len(after)==len(before)+1
report.write_text(json.dumps(dict(slot=slot,generation=gen+1,instance_id=iid,cell=cell,row=cell//18+1,column=cell%18+1,magazine=30,existing_items_preserved=len(before)),indent=2))
unreal.log('PLAYER_AKM_GRANT_PASS')
