"""Publish four corrected body paths, preserving all current hem and sleeve routes."""
import json,copy,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'FacingFix20261020'
saved=json.loads((OUT/'saved_assets.json').read_text());initial=json.loads((OUT/'modular_outfits-before.json').read_text(encoding='utf-8-sig'))['items']['ue_blue_mage_robe']
if not saved.get('completed'):raise RuntimeError('Facing repair assets have not all been saved')
spec=importlib.util.spec_from_file_location('robe_facing_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');before=json.loads(text)['items']['ue_blue_mage_robe'];recipe=copy.deepcopy(before)
for profile in ('Body','Jason'):
    for field,suffix in (('rig_meshes',''),('owner_body_meshes','_Owner')):
        target=saved['saved']['Body/'+profile+suffix]['asset']
        if before[field][profile] not in (initial[field][profile],target):raise RuntimeError('Robe body route changed during authoring '+profile)
        recipe[field][profile]=target
recipe['facing_revision']='20261020-native-forward-v1';out=e.replace(text,['items','ue_blue_mage_robe'],recipe)
if path.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed; retry scoped publication')
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+out.encode('utf-8'))
mainpath=R/'saved_assets.json';main=json.loads(mainpath.read_text());main['saved'].update(saved['saved']);main['facing_revision']=recipe['facing_revision'];main['active_body_revision']='FacingFix20261020';mainpath.write_text(json.dumps(main,indent=2),encoding='utf-8')
(OUT/'published.json').write_text(json.dumps(dict(completed=True,body_variants=4,recipe=recipe,before=before,cloth_revision=recipe['cloth_revision'],hem_revision=recipe['stair_visibility_revision'],runtime_tested=False,network_tested=False,icon_png_unchanged=True),ensure_ascii=False,indent=2),encoding='utf-8');print('ROBE_FACING_PUBLISHED 4',flush=True)
