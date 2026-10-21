"""Publish only the crown appearance and its game icons; retain the wider visor."""
import hashlib, importlib.util, json, shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SteelArmet20261019/CrownRefine20261020'
saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed'):raise RuntimeError('Save crown assets before publication')
for key,file in [('mesh','helmet.json'),('pickup','helmet.json'),('icon','display.json')]:
    if saved['saved'][key]['sha256']!=hashlib.sha256((R/'Authored'/file).read_bytes()).hexdigest():
        raise RuntimeError('Save current crown geometry '+key)
if saved['icon_sha256']!=hashlib.sha256((R/'ue_steel_armet.png').read_bytes()).hexdigest():
    raise RuntimeError('Save current crown icon')
spec=importlib.util.spec_from_file_location('crown_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
body=P/'Content/ColdSteelData/player_body.json';items=P/'Content/ColdSteelData/items.json'
raw=[p.read_bytes() for p in (body,items)];text=[b.decode('utf-8-sig') for b in raw]
cfg=json.loads(text[0]);recipe=cfg['head_equipment']['ue_steel_armet']
if recipe['static_mesh']!=saved['source_mesh']:
    raise RuntimeError('Active helmet changed during authoring; retain new selection')
overlay=recipe['first_person_overlay']
text[0]=entries.replace(text[0],['head_equipment','ue_steel_armet','static_mesh'],saved['mesh'])
fields=dict(world_mesh=saved['pickup'],ue_equipment_icon_mesh=saved['icon'],
    ue_icon_pitch=0,ue_icon_yaw=0,ue_icon='Icons/SteelArmet20261019/CrownRefine20261020/ue_steel_armet.png')
for key,value in fields.items():text[1]=entries.replace(text[1],['ue_steel_armet',key],value)
if any(p.read_bytes()!=old for p,old in zip((body,items),raw)):
    raise RuntimeError('Equipment configuration changed; retry scoped publication')
for path,old,new in zip((body,items),raw,text):
    backup=R/(path.stem+'-before.json')
    if not backup.exists():backup.write_bytes(old)
    if path.name == 'player_body.json':
        entries.commit_player_body(path,old,new,owned_paths=[('head_equipment','ue_steel_armet','static_mesh')],producer=__file__)
    else:
        path.write_bytes((b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+new.encode('utf-8'))
icons=P/'Content/ColdSteelData/Icons'
folder=icons/'SteelArmet20261019/CrownRefine20261020';folder.mkdir(parents=True,exist_ok=True)
shutil.copy2(R/'ue_steel_armet.png',folder/'ue_steel_armet.png')
fallback=icons/'ue_steel_armet.png'
backup=R/'fallback-icon-before.png'
if fallback.exists() and not backup.exists():shutil.copy2(fallback,backup)
shutil.copy2(R/'ue_steel_armet.png',fallback)
(R/'published.json').write_text(json.dumps(dict(completed=True,
    revision='crown-fold-20261020',mesh=saved['mesh'],pickup=saved['pickup'],icon=saved['icon'],
    retained_first_person_overlay=overlay,head_fit_changed=False,gameplay_changed=False,
    runtime_tested=False),indent=2),encoding='utf-8')
print('STEEL_ARMET_CROWN_PUBLISHED',flush=True)
