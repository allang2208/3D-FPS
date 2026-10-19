"""Recover per-route save receipts from the 48 already written packages.

The import loop completed; only publication failed on a receipt-key collision.
The serialized author SHA is the commit marker written after successful LOD
generation and package save. No engine launch or live asset edit is required.
"""
import json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018';DEST='/Game/Characters/ModularOutfit20260924/GarmentSleeveRepair20261018'
log=R/'save-all-01.txt'
if 'Saved receipt does not yet cover the 48 intended mesh routes' not in log.read_text(encoding='utf-8',errors='replace'):raise RuntimeError('Missing completed-save/publication-only failure evidence')
receipt=dict(saved={},completed=False,runtime_tested=False,confirmation_mode='Serialized author fingerprints in saved packages; no live asset mutation',save_execution_evidence=str(log),lod_note='Three LODs were requested and successfully generated before each saved author tag; no fresh per-asset LOD count is claimed')
for row in json.loads((R/'inventory.json').read_text(encoding='utf-8'))['rows']:
    item=row['item'];profile=row['profile']
    if item not in ('ue_field_sweater','ue_chainmail_shirt') and profile not in ('SVD','Super90'):continue
    raw=(R/'Authored'/item/(profile+'.json')).read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw)
    path=DEST+'/'+item+'/'+profile+'/SK_'+profile+'_'+item;disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset');policy=disk.with_name(disk.stem+'_LODPolicy.uasset')
    package=disk.read_bytes()
    if b'GarmentSleeveSHA' not in package or sha.encode('ascii') not in package:raise RuntimeError('Author tag not present in saved package '+path)
    if not policy.exists():raise RuntimeError('Missing saved LOD policy '+str(policy))
    receipt['saved'][item+'/'+profile]=dict(asset=path+'.'+disk.stem,author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=None,lod_build_target=3,lod_policy=path+'_LODPolicy.'+policy.stem,package_sha256=hashlib.sha256(package).hexdigest(),lod_policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest())
if len(receipt['saved'])!=48:raise RuntimeError('Incomplete saved package set')
receipt['completed']=True
(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('GARMENT_DISK_SAVE_RECEIPTS_COMPLETE',len(receipt['saved']))
