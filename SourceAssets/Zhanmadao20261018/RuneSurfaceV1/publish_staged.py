"""Publish already-saved new UE material packages under the normal integration mutex."""
import json,shutil,runpy
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
file=P/'import_receipt.json';receipt=json.loads(file.read_text(encoding='utf-8'))
if not receipt.get('staged_assets_saved'):raise RuntimeError('Complete isolated material saving first')
transfers=[]
for asset in receipt['assets']:
    package=asset.split('.')[0]
    if not package.startswith('/Game/Weapons/Zhanmadao20261018/RuneSurfaceV1/Materials/'):
        raise RuntimeError('Unexpected package outside this task: '+package)
    relative=Path(package.removeprefix('/Game/')).with_suffix('.uasset')
    source=P/'AssetHost/Content'/relative;target=ROOT/'Content'/relative
    if target.exists():raise RuntimeError('Preserved existing material package: '+str(target))
    transfers.append((source,target))
for source,target in transfers:
    target.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ['.uexp','.ubulk','.uptnl']:
        extra=source.with_suffix(suffix)
        if extra.exists():shutil.copy2(extra,target.with_suffix(suffix))
    temporary=target.with_suffix('.uasset.staging');shutil.copy2(source,temporary);temporary.rename(target)
receipt.update(assets_saved=True,published_project=str(ROOT))
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
catalog_path=DATA/'zhanmadao-modules.json';map_path=DATA/'whirlwind-temporal-materials.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
catalog=runpy.run_path(str(P/'catalog_extension.py'))['extend'](catalog)
mapping=json.loads(map_path.read_text(encoding='utf-8-sig'));mapping.update(receipt['temporal_bindings'])
for path,value in [(catalog_path,catalog),(map_path,mapping)]:
    backup=P/'Before'/path.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    temporary=path.with_suffix('.zhan-runes.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
receipt.update(complete=True,catalog_saved=True,blade_choices=list(receipt['bindings']),
    runes=['strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune'])
file.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_NATIVE_RUNE_PACKAGES_AND_BINDINGS_PUBLISHED',len(transfers))
