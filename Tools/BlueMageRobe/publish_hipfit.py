"""Publish only the four repaired body routes; preserve sleeves and restored calves."""
import json,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'HipFit20261019';saved=json.loads((OUT/'saved_assets.json').read_text())
if not saved.get('completed'):raise RuntimeError('Repaired bodies have not all been saved')
spec=importlib.util.spec_from_file_location('robe_hipfit_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');config=json.loads(text);recipe=dict(config['items']['ue_blue_mage_robe']);before=dict(recipe)
recipe['rig_meshes']=dict(recipe['rig_meshes']);recipe['owner_body_meshes']=dict(recipe['owner_body_meshes'])
for profile in ('Body','Jason'):
    recipe['rig_meshes'][profile]=saved['saved']['Body/'+profile]['asset'];recipe['owner_body_meshes'][profile]=saved['saved']['Body/'+profile+'_Owner']['asset']
recipe['hip_fit_revision']='20261019-v1';updated=entries.replace(text,['items','ue_blue_mage_robe'],recipe)
if path.read_bytes()!=raw:raise RuntimeError('Shared outfit catalog changed during publication; retry')
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
main_path=R/'saved_assets.json';main=json.loads(main_path.read_text());main['saved'].update(saved['saved']);main['hip_fit_revision']='20261019-v1';main_path.write_text(json.dumps(main,indent=2),encoding='utf-8')
(OUT/'published.json').write_text(json.dumps(dict(completed=True,before=before,recipe=recipe,body_variants=4,first_person_sleeves_unchanged=True,calf_underlayers_unchanged=before.get('underlayer_meshes')==recipe.get('underlayer_meshes'),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('BLUE_ROBE_HIPFIT_PUBLISHED 4 body variants')
