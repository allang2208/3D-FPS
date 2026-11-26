"""Replace only robe skin mappings, retaining current skirt/pants/boot repairs."""
import hashlib, importlib.util, json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/WristContinuity20261020'
saved=json.loads((R/'saved_assets.json').read_text())
authored=json.loads((R/'authored.json').read_text())
if not saved.get('completed'):raise RuntimeError('Finish wrist skin saves first')
path=P/'Content/ColdSteelData/modular_outfits.json'
raw=path.read_bytes();text=raw.decode('utf-8-sig')
robe=json.loads(text)['items']['ue_blue_mage_robe']
spec=importlib.util.spec_from_file_location('wrist_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
for row in authored['rows']:
    result=saved['saved'][row['original']]
    if result['source_sha256']!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():
        raise RuntimeError('Wrist source changed since saving '+row['key'])
    if robe['underlayer_meshes'][row['original']]!=result['previous']:
        raise RuntimeError('Robe skin route changed; preserve concurrent changes')
    text=entries.replace(text,['items','ue_blue_mage_robe','underlayer_meshes',row['original']],result['asset'])
key='wrist_continuity_revision'
text=entries.replace(text,['items','ue_blue_mage_robe',key],'20261020-native-overlap-v1') if key in robe else entries.insert(text,['items','ue_blue_mage_robe'],key,'20261020-native-overlap-v1')
if path.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed during publication; retry')
backup=R/'modular_outfits-before.json'
if not backup.exists():backup.write_bytes(raw)
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,skin_variants=len(saved['saved']),
    skirt_and_hem_materials_preserved=True,first_person_sleeves_preserved=True,
    source_positions_preserved=True,runtime_tested=False),indent=2),encoding='utf-8')
print('ROBE_WRIST_PUBLISHED',len(saved['saved']),flush=True)
