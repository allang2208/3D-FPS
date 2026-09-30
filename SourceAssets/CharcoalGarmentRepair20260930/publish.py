"""Patch only charcoal references after assets have actually been saved."""
import sys,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/CharcoalGarmentRepair20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
saved=read(R/'saved-assets.json');before=read(R/'before-item.json')
config_path=P/'Content/ColdSteelData/modular_outfits.json';config=read(config_path);item=config['items']['ue_field_sweater_charcoal']
for profile in ['Body','Traversal']:
    path=saved[profile]['asset']
    if item['rig_meshes'][profile] not in [before['rig_meshes'][profile],path,'/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/'+('BodyV2/SK_Body_Charcoal.SK_Body_Charcoal' if profile=='Body' else 'Traversal/SK_Traversal_Charcoal.SK_Traversal_Charcoal')]:raise RuntimeError('Concurrent charcoal binding edit: '+profile)
    if not asset_file(path).is_file():raise RuntimeError('Unsaved garment asset '+profile)
    saved[profile]['asset_sha256']=digest(asset_file(path))
    item['rig_meshes'][profile]=path
if item['world_covers'] not in [before['world_covers'],[1,3],[1,3,4]]:raise RuntimeError('Concurrent charcoal coverage edit')
item['world_covers']=[1,3,4]
temporary=config_path.with_name('modular_outfits.charcoal-repair.tmp');write(temporary,config);temporary.replace(config_path)
items_path=P/'Content/ColdSteelData/items.json';items=read(items_path)
old_pickup='/Game/Characters/ModularOutfit20260924/FieldSweaterKnit20260929/Pickups/SM_Charcoal_Garment.SM_Charcoal_Garment'
if items['ue_field_sweater_charcoal']['world_mesh'] not in [old_pickup,saved['pickup'],'/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/Pickups/SM_Charcoal_Garment.SM_Charcoal_Garment']:raise RuntimeError('Concurrent charcoal pickup edit')
if not asset_file(saved['pickup']).is_file():raise RuntimeError('Unsaved charcoal pickup')
items['ue_field_sweater_charcoal']['world_mesh']=saved['pickup']
temporary=items_path.with_name('items.charcoal-repair.tmp');write(temporary,items);temporary.replace(items_path)
write(R/'published.json',dict(item='ue_field_sweater_charcoal',assets=saved,world_covers=[1,3,4],runtime_tested=False))
print('CHARCOAL_REFERENCES_PUBLISHED')
