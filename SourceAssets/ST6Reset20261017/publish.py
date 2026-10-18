"""Merge only the completed ST6 recipe and size into the live catalogs."""
import hashlib,json,shutil,sys
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1];OLD=O.parent/'BenelliM4Super9020261006';sys.path.insert(0,str(O))
from recipe import apply
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt.get('sleeves_completed'):raise RuntimeError('Sleeve assets are not saved')
if not (O/'material_receipt.json').exists():raise RuntimeError('Native fabric materials are not saved')
if not (O/'display_receipt.json').exists():raise RuntimeError('ST6 display model and icon are not saved')
rows=json.loads((O/'sleeve_manifest.json').read_text())
for row in rows:
    file=Path(row['file']);raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if receipt['saved'][row['profile']]['sha256']!=sha:raise RuntimeError('Unsaved sleeve source')
    target=OLD/'EquipmentAuthored'/file.name
    if hashlib.sha256(target.read_bytes()).hexdigest() not in (sha,row['previous_source_sha256']):raise RuntimeError('ST6 source changed during authoring '+row['profile'])
    shutil.copy2(file,target)
    cached=OLD/'EquipmentSaved'/file.name
    cached.write_text(json.dumps(dict(profile=row['profile'],item='ue_st6_sleeves',mesh=row['asset'],sha256=sha,runtime_tested=False,repair='ST6Reset20261017'),indent=2))
path=R/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(path.read_text(encoding='utf-8-sig'));apply(config)
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=R/'Content/ColdSteelData/items.json'
items=json.loads(path.read_text(encoding='utf-8-sig'))
item=items['ue_st6_sleeves'];item['grid_w']=3;item['grid_h']=3
item['desc']='深灰织物战术上衣，胸背与肩部采用分区拼接，长袖保留收紧袖口与自然褶皱。'
path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
icon=R/'Content/ColdSteelData/Icons/Super90Source20261006/ue_st6_sleeves.png'
backup=O/'Before/ue_st6_sleeves.png'
if icon.exists() and not backup.exists():shutil.copy2(icon,backup)
shutil.copy2(O/'ue_st6_sleeves.png',icon)
shutil.copy2(O/'ue_st6_sleeves.png',OLD/'EquipmentIcons/ue_st6_sleeves.png')
pickup_backup=O/'Before/SM_ue_st6_sleeves.fbx'
if not pickup_backup.exists():shutil.copy2(OLD/'Exports/SM_ue_st6_sleeves.fbx',pickup_backup)
shutil.copy2(O/'SM_ue_st6_sleeves.fbx',OLD/'Exports/SM_ue_st6_sleeves.fbx')
(O/'published.json').write_text(json.dumps(dict(item='ue_st6_sleeves',grid=[3,3],restored_bindings=len(rows),native_body_materials=True,game_run=False),indent=2))
print('ST6_RECIPE_AND_3X3_PUBLISHED',flush=True)
