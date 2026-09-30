"""Publish the saved FP family only; retain Body and other outfits verbatim."""
import json,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
path=P/'Content/ColdSteelData/modular_outfits.json';original=path.read_bytes();config=json.loads(original.decode('utf-8-sig'))
item=config['items']['ue_field_sweater'];before=read(R/'before.json')['recipe'];results={}
for profile,old_path in before['rig_meshes'].items():
 if profile=='Body':continue
 receipt=read(R/'Saved'/profile/'saved.json');source=read(R/'Before'/profile/'paths.json')
 if item['rig_meshes'][profile] not in (old_path,receipt['asset']):raise RuntimeError('Concurrent sleeve reference edit: '+profile)
 if digest(asset_file(source['shirt']))!=source['shirt_sha256'] or digest(asset_file(source['skin']))!=source['skin_sha256']:raise RuntimeError('Author source changed: '+profile)
 if digest(asset_file(receipt['asset']))!=receipt['asset_sha256']:raise RuntimeError('Saved asset changed: '+profile)
 if digest(R/'Authored'/(profile+'.json'))!=receipt['author_sha256']:raise RuntimeError('Author not saved: '+profile)
 item['rig_meshes'][profile]=receipt['asset'];results[profile]=receipt
write(R/'publication-before.json',json.loads(original.decode('utf-8-sig')))
if path.read_bytes()!=original:raise RuntimeError('Configuration changed before publication')
temporary=path.with_name('modular_outfits.field-native.tmp');write(temporary,config);temporary.replace(path)
write(R/'saved-assets.json',results)
write(R/'published.json',dict(item='ue_field_sweater',profiles={p:r['asset'] for p,r in results.items()},body=item['rig_meshes']['Body'],world_covers=item.get('world_covers'),runtime_tested=False,config_sha256=digest(path)))
print('FIELD_NATIVE_FAMILY_PUBLISHED',len(results),'runtime_tested=False')
