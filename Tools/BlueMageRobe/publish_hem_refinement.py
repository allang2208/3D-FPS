"""Publish the saved material revision without replacing any outfit routes."""
import json,importlib.util,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'HemRefine20261020'
saved=json.loads((OUT/'saved_assets.json').read_text())
if not saved.get('completed'):raise RuntimeError('Refined hem materials/icon are not all saved')
expected=hashlib.sha256((P/'Tools/BlueMageRobe/hem_conform.hlsl').read_text().encode()+(P/'Tools/BlueMageRobe/hem_materials.py').read_bytes()).hexdigest()
if saved['shader_revision']!=expected:raise RuntimeError('Final material source changed before publication; save the current revision first')
spec=importlib.util.spec_from_file_location('robe_refinement_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
p=P/'Content/ColdSteelData/modular_outfits.json';raw=p.read_bytes();s=raw.decode('utf-8-sig');cfg=json.loads(s);r=cfg['items']['ue_blue_mage_robe'];mapping=r['underlayer_meshes']
for row in saved['meshes'].values():
    if row['asset'] not in mapping.values():raise RuntimeError('Underlayer routing changed during material authoring')
s=e.replace(s,['items','ue_blue_mage_robe','stair_visibility_revision'],'20261020-cross-section-v3')
if p.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed; retry publication')
p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+s.encode('utf-8'))
(OUT/'published.json').write_text(json.dumps(dict(completed=True,underlayers=len(mapping),updated_material_meshes=len(saved['meshes']),shader_revision=saved['shader_revision'],facing_revision=r['facing_revision'],cloth_revision=r['cloth_revision'],icon_png_updated=True,runtime_tested=False,network_transport_tested=False),indent=2),encoding='utf-8');print('ROBE_HEM_REFINEMENT_PUBLISHED',len(mapping),flush=True)
