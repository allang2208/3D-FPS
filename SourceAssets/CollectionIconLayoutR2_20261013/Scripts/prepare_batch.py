"""Prepare one icon-only batch from the current collection models and catalog."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
catalog=json.loads((PROJECT/'Content/ColdSteelData/items.json').read_text('utf-8-sig'))
design=json.loads((PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json').read_text('utf-8'))
current={item['id']:item for item in design['items']}
directions=dict(USB=(-6,-8,7),Tape=(6,-8,8),Case=(6,-8,7),Archive=(5,-8,10),
                Alloy=(0,-8,11),Assembly=(2,-9,13),Resin=(0,-7,12),Wood=(0,-8,12),Precision=(2,-9,13),
                RAM=(0,-8,13),NIC=(-3,-9,13),HDD=(2,-9,13),SSD=(2,-9,13),CPU=(5,-8,12),
                GPU=(-2,-9,13),RAID=(-4,-8,13),Compute=(-2,-9,11))
batch=dict(stage='prepared',scope='Existing modeled search collectibles only; equipment and weapons excluded',assets={})
legacy=json.loads((PROJECT/'SourceAssets/ServerNeutralPCB20261013/Receipts/legacy-appearance.json').read_text('utf-8'))
for bundle in ('SearchDocuments20261012','SearchMaintenance20261012','SearchServerEquipment20261013','ServerOriginalMarks20261013','ServerNeutralPCB20261013'):
    source=PROJECT/'SourceAssets'/bundle/'model_manifest.json'
    for key,spec in json.loads(source.read_text('utf-8'))['assets'].items():
        identifier=spec['id'];item=catalog[identifier];definition=current[identifier]
        # The three reference-remodeled hardware pieces supersede the first batch.
        active_glb=(PROJECT/definition['model']['glb']).resolve()
        if Path(spec['glb']).resolve()!=active_glb:continue
        original=PROJECT/'Content/ColdSteelData'/item['ue_icon']
        backup=ROOT/'PreviousIcons'/item['ue_icon'];backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(original,backup)
        aliases=[]
        for alias in legacy['icons']:
            if alias['id']!=identifier:continue
            target=Path(alias['path']);saved=ROOT/'PreviousIcons'/target.relative_to(PROJECT/'Content/ColdSteelData')
            saved.parent.mkdir(parents=True,exist_ok=True)
            if not saved.exists():shutil.copy2(target,saved)
            aliases.append(dict(path=str(target),backup=str(saved)))
        batch['assets'][identifier]={**spec,'grid_w':definition['grid_w'],'grid_h':definition['grid_h'],
            'camera_direction':directions[key],'runtime_icon':str(original),'ue_icon':item['ue_icon'],
            'source_manifest':str(source),'source_key':key,'previous_icon':str(backup),'legacy_aliases':aliases}
for folder in ('Icons','Receipts'): (ROOT/folder).mkdir(parents=True,exist_ok=True)
(ROOT/'model_manifest.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COLLECTION_ICON_BATCH_PREPARED',len(batch['assets']))
