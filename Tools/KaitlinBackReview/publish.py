"""Change only the saved female robe's world route."""
import hashlib,json,os,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/KaitlinBackReview20261117'
saved=json.loads((R/'saved.json').read_text())
if not saved['saved']:raise RuntimeError('Save the asset first')
path=P/'Content/ColdSteelData/modular_outfits.json';before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
keys=('body_variants','kaitlin','items','ue_blue_mage_robe','rig_meshes','Kaitlin')
node=cfg
for key in keys[:-1]:node=node[key]
if node[keys[-1]] not in [saved['source'],saved['asset']]:raise RuntimeError('Female robe route changed concurrently')
node[keys[-1]]=saved['asset']
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
from json_entries import replace
text=replace(before.decode('utf-8-sig'),list(keys),saved['asset'])
output=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
backup=R/'modular_outfits_before.json'
if not backup.exists():backup.write_bytes(before)
temporary=path.with_name('modular_outfits.kaitlin-back.tmp');temporary.write_bytes(output)
if path.read_bytes()!=before:raise RuntimeError('Concurrent outfit edit; preserve current configuration')
os.replace(temporary,path)
receipt=dict(owned_path=list(keys),before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(output).hexdigest())
(R/'published.json').write_text(json.dumps(dict(asset=saved['asset'],config_receipt=receipt),indent=2))
print('KAITLIN_BACK_PUBLISHED',saved['asset'])
