"""Switch only the robe's pants routes after all native fits have been saved."""
import json, hashlib, importlib.util
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/UnderRobeFit20261020'
saved=json.loads((R/'saved_assets.json').read_text());authored=json.loads((R/'authored.json').read_text())
if not saved.get('completed'):raise RuntimeError('Finish saving all inner trousers before publication')
revision=hashlib.sha256((P/'Tools/BlueMageRobe/hem_conform.hlsl').read_text().encode()+(P/'Tools/BlueMageRobe/hem_visibility.hlsl').read_text().encode()+(P/'Tools/BlueMageRobe/hem_materials.py').read_bytes()).hexdigest()
if saved['shader_revision']!=revision:raise RuntimeError('Current hem material revision has not been saved')
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');cfg=json.loads(text)
robe=cfg['items']['ue_blue_mage_robe'];mapping=dict(robe['underlayer_meshes'])
for row in authored['rows']:
    target=saved['underlayers'][row['source']]
    if mapping.get(row['source']) not in (row['previous_underlayer'],target):raise RuntimeError('Robe pants route changed during production: '+row['source'])
    source_sha=hashlib.sha256(Path(row['authored']).read_bytes()+revision.encode()).hexdigest()
    if saved['saved'][row['key']]['source_sha256']!=source_sha:raise RuntimeError('Save the latest authored fit for '+row['key'])
    mapping[row['source']]=target
spec=importlib.util.spec_from_file_location('inner_fit_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
text=entries.replace(text,['items','ue_blue_mage_robe','underlayer_meshes'],mapping)
if 'underlayer_fit_revision' in robe:text=entries.replace(text,['items','ue_blue_mage_robe','underlayer_fit_revision'],authored['revision'])
else:text=entries.insert(text,['items','ue_blue_mage_robe'],'underlayer_fit_revision',authored['revision'])
if path.read_bytes()!=raw:raise RuntimeError('Outfit definitions changed; retry scoped publication')
(R/'modular_outfits-before.json').write_bytes(raw)
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,revision=authored['revision'],pants_routes=len(saved['underlayers']),total_underlayers=len(mapping),original_equipment_unchanged=True,body_and_boot_routes_unchanged=True,full_legs_retained=True,cloth_physics_unchanged=True,cpp_changed=False,runtime_tested=False,network_tested=False),indent=2),encoding='utf-8')
print('ROBE_INNER_PANTS_PUBLISHED',len(saved['underlayers']),flush=True)
