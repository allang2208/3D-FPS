"""Only update the robe's inner-layer mapping after every partition is saved."""
import json,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/HemContinuity20261019'
s=importlib.util.spec_from_file_location('robe_stair_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
saved=json.loads((R/'saved_assets.json').read_text());inputs=json.loads((R/'inputs.json').read_text())
if not saved.get('completed'):raise RuntimeError('Stair partition packages not all saved')
path=P/'Content/ColdSteelData/modular_outfits.json';before=path.read_bytes();text=before.decode('utf-8-sig');cfg=json.loads(text);robe=cfg['items']['ue_blue_mage_robe'];mapping=dict(robe['underlayer_meshes'])
for key,value in saved['underlayers'].items():
    if mapping.get(key) not in (inputs['underlayer_meshes'][key],value):raise RuntimeError('Robe mapping changed during authoring: '+key)
    mapping[key]=value
out=e.replace(text,['items','ue_blue_mage_robe','underlayer_meshes'],mapping)
if 'stair_visibility_revision' in robe:out=e.replace(out,['items','ue_blue_mage_robe','stair_visibility_revision'],'20261019-continuous-hem-v2')
else:out=e.insert(out,['items','ue_blue_mage_robe'],'stair_visibility_revision','20261019-continuous-hem-v2')
if path.read_bytes()!=before:raise RuntimeError('Outfit configuration changed; retry scoped publication')
(R/'modular_outfits-before.json').write_bytes(before);path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+out.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,underlayer_count=len(saved['underlayers']),saved_partition_count=len(saved['saved']),weapon_routing='shared world and owner body, all weapon families',network='each rendered pawn uses its own cloth envelope, foot contacts and replicated outfit',cloth_revision=robe['cloth_revision'],contract='continuous calf and low-thigh overlap; exposed surface preserved; draw-only contraction inside actual hem; no ankle caps or whole-calf hiding',runtime_tested=False),indent=2),encoding='utf-8');print('ROBE_HEM_CONTINUITY_PUBLISHED',len(saved['underlayers']),flush=True)
