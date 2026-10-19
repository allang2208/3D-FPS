"""Commit the saved robe body and inner-layer routes without editing other gear."""
import json,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';F=R/'LegFit20261019'
saved=json.loads((F/'saved_assets.json').read_text());root=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed') or not saved.get('collision_pose_bound'):raise RuntimeError('Leg-fit packages and collision pose binding have not finished saving')
file=P/'Content/ColdSteelData/modular_outfits.json';raw=file.read_bytes();text=raw.decode('utf-8-sig');config=json.loads(text);recipe=config['items']['ue_blue_mage_robe']
for profile in ('Body','Jason'):
    needed={r.get('native_bare_skin',r['base']) for r in config['profiles'].values() if r['rig_profile']==profile}
    for item in config['items'].values():
        if item.get('slot') in (13,15):
            needed.add(item.get('rig_meshes',{}).get(profile))
            needed.update(fit.get(profile) for fit in item.get('shoe_fit_meshes',{}).values())
        if item.get('slot')==3:needed.add(item.get('skin_meshes',{}).get(profile))
    missing={p for p in needed if p and p not in saved['underlayers']}
    if missing:raise RuntimeError('New inner-layer source needs authoring '+str(missing))
    recipe['rig_meshes'][profile]=saved['saved']['Body/'+profile]['asset'];recipe['owner_body_meshes'][profile]=saved['saved']['Body/'+profile+'_Owner']['asset']
revision=saved.get('leg_fit_revision','20261019-v2');recipe['underlayer_meshes']=saved['underlayers'];recipe['leg_fit_revision']=revision
spec=importlib.util.spec_from_file_location('robe_legfit_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
new=entries.replace(text,['items','ue_blue_mage_robe'],recipe)
if file.read_bytes()!=raw:raise RuntimeError('Outfit definitions changed during scoped update; retry')
before=F/'Before';before.mkdir(exist_ok=True)
if not (before/'modular_outfits.json').exists():(before/'modular_outfits.json').write_bytes(raw)
file.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+new.encode('utf-8'))
for key,row in saved['saved'].items():
    if key.startswith('Body/'):root['saved'][key]=row
root['underlayers']=saved['underlayers'];root['leg_fit_revision']=revision;(R/'saved_assets.json').write_text(json.dumps(root,indent=2),encoding='utf-8')
report=dict(completed=True,recipe=recipe,underlayer_sources=len(saved['underlayers']),saved_meshes=len(saved['saved']),runtime_tested=False,original_gear_changed=False)
(F/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
published=json.loads((R/'published.json').read_text(encoding='utf-8'));published['recipe']=recipe;published['leg_fit_revision']=revision;published['runtime_tested']=False;(R/'published.json').write_text(json.dumps(published,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLUE_ROBE_LEGFIT_PUBLISHED',len(saved['underlayers']),'inner-layer sources',len(saved['saved']),'saved meshes')
