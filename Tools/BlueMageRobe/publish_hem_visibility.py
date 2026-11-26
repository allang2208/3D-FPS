"""Record only the saved coverage revision; keep fitted mesh routes unchanged."""
import json,hashlib,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/OwnerLayerRepair20261020'
saved=json.loads((R/'saved_assets.json').read_text())
revision=hashlib.sha256((P/'Tools/BlueMageRobe/hem_conform.hlsl').read_text().encode()+(P/'Tools/BlueMageRobe/hem_visibility.hlsl').read_text().encode()+(P/'Tools/BlueMageRobe/hem_materials.py').read_bytes()).hexdigest()
if not saved.get('completed') or saved.get('shader_revision')!=revision:raise RuntimeError('Save the current coverage materials before publication')
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');cfg=json.loads(text)
robe=cfg['items']['ue_blue_mage_robe']
if robe['underlayer_meshes']!=saved['mapping']:raise RuntimeError('Robe inner routes changed during saving; include the new routes first')
spec=importlib.util.spec_from_file_location('robe_coverage_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
key='underlayer_visibility_revision';value='20261020-dynamic-hem-mask-v5'
text=entries.replace(text,['items','ue_blue_mage_robe',key],value) if key in robe else entries.insert(text,['items','ue_blue_mage_robe'],key,value)
if path.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed; retry scoped publication')
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,revision=value,shader_revision=revision,updated_inner_meshes=len(saved['meshes']),underlayer_routes=len(saved['mapping']),geometry_unchanged=True,fitted_pants_retained=True,cloth_physics_unchanged=True,runtime_tested=False),indent=2),encoding='utf-8')
print('ROBE_COVERAGE_PUBLISHED',len(saved['meshes']),flush=True)
