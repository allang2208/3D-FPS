"""Save only the two repaired field-sweater bindings and their body coverage."""
import json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
path=P/'Content/ColdSteelData/modular_outfits.json';original=path.read_bytes();config=json.loads(original.decode('utf-8-sig'))
item=config['items']['ue_field_sweater'];before=read(R/'before.json')['recipe'];saved=read(R/'saved-assets.json')
for profile in ['Body','Traversal']:
 receipt=saved[profile];source=read(R/'Before'/profile/'paths.json')
 if item['rig_meshes'][profile] not in [before['rig_meshes'][profile],receipt['asset']]:raise RuntimeError('Concurrent field-sweater edit: '+profile)
 if digest(asset_file(source['shirt']))!=source['shirt_sha256'] or digest(asset_file(source['skin']))!=source['skin_sha256']:raise RuntimeError('Author source changed: '+profile)
 if digest(asset_file(receipt['asset']))!=receipt['asset_sha256']:raise RuntimeError('Saved garment changed: '+profile)
 item['rig_meshes'][profile]=receipt['asset']
if item.get('world_covers') not in [before.get('world_covers'),[0,1,3,4]]:raise RuntimeError('Concurrent body coverage edit')
item['world_covers']=[0,1,3,4]
write(R/'publication-before.json',json.loads(original.decode('utf-8-sig')))
if path.read_bytes()!=original:raise RuntimeError('Configuration changed before publication')
temporary=path.with_name('modular_outfits.field-surface.tmp');write(temporary,config);temporary.replace(path)
write(R/'published.json',dict(item='ue_field_sweater',profiles={k:v['asset'] for k,v in saved.items()},world_covers=[0,1,3,4],runtime_tested=False,config_sha256=digest(path)))
print('FIELD_SURFACE_PUBLISHED',len(saved),'runtime_tested=False')
