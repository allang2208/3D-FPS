"""Upgrade the shared bare-skin parent materials with skin_recipe (commandlet, UE closed).

Targets the skin parents found by snapshot_ue.py, except the Super90-specific
SkinClean/JointSurface parents that already carry this look. Every recipe step
must match exactly once, else that material is left untouched and reported.
"""
import json, hashlib, shutil, sys
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareHandAudit20261016'
sys.path.insert(0, str(R))
from skin_recipe import upgrade, MARK
E = u.EditorAssetLibrary; L = u.MaterialEditingLibrary
OUT = R / 'Materials'; OUT.mkdir(exist_ok=True)
inv = json.loads((R / 'inventory.json').read_text())
rows = []
for pk in inv['skin_parents']:
    if 'Super90' in pk: rows.append(dict(package=pk, skipped='Super90 parent already carries this look')); continue
    if 'PlayerBodySkin' in pk: rows.append(dict(package=pk, skipped='third-person body skin; out of scope')); continue
    path = pk + '.' + pk.split('/')[-1]
    m = u.load_asset(path)
    node = L.get_material_property_input_node(m, u.MaterialProperty.MP_NORMAL)
    code = str(node.get_editor_property('code'))
    if code.startswith(MARK): rows.append(dict(package=pk, skipped='already upgraded')); continue
    new, applied, missing = upgrade(code)
    if missing:
        rows.append(dict(package=pk, skipped='recipe mismatch', missing=missing)); print('BARE_V8_MATERIAL_SKIP', pk, missing, flush=True); continue
    file = P / 'Content' / (pk.removeprefix('/Game/') + '.uasset')
    backup = R / 'Before' / file.relative_to(P); backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): shutil.copy2(file, backup)
    (OUT / (pk.split('/')[-1] + '.before.hlsl')).write_text(code)
    node.set_editor_property('code', new)
    errors = L.recompile_material(m)
    if errors: raise RuntimeError('Material compiler errors: %s %s' % (pk, errors))
    E.set_metadata_tag(m, 'BareSkinV8', '20261016: Super90 clean-up + wrist transition on shared parameters')
    if not E.save_loaded_asset(m, False): raise RuntimeError('Could not save ' + pk)
    (OUT / (pk.split('/')[-1] + '.hlsl')).write_text(new)
    rows.append(dict(package=pk, applied=len(applied), shader_sha256=hashlib.sha256(new.encode()).hexdigest(), runtime_tested=False))
    print('BARE_V8_MATERIAL_SAVED', pk, flush=True)
(R / 'materials_receipt.json').write_text(json.dumps(rows, indent=1))
print('BARE_V8_MATERIAL_COMPLETE', len(rows), flush=True)
