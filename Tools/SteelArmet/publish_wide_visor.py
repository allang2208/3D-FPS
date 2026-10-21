"""Switch only the steel armet owner overlay, preserving all other equipment data."""
import hashlib, importlib.util, json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/SteelArmet20261019/FirstPersonWide20261020'
saved=json.loads((R/'saved_assets.json').read_text())
sha=hashlib.sha256((R/'Textures/T_SteelArmet_Visor.png').read_bytes()).hexdigest()
if not saved.get('completed') or saved.get('source_sha256')!=sha:
    raise RuntimeError('Save the current wider visor before publication')
spec=importlib.util.spec_from_file_location('wide_visor_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
path=P/'Content/ColdSteelData/player_body.json'
raw=path.read_bytes();text=raw.decode('utf-8-sig')
old=json.loads(text)['head_equipment']['ue_steel_armet']['first_person_overlay']
text=entries.replace(text,['head_equipment','ue_steel_armet','first_person_overlay'],saved['visor_texture'])
backup=R/'player_body-before.json'
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Body configuration changed; retry scoped publication')
entries.commit_player_body(path,raw,text,owned_paths=[('head_equipment','ue_steel_armet','first_person_overlay')],producer=__file__)
(R/'published.json').write_text(json.dumps(dict(completed=True,
    previous_overlay=old,first_person_overlay=saved['visor_texture'],
    clear_center_height_fraction=saved['clear_center_height_fraction'],
    clear_max_width_fraction=saved['clear_max_width_fraction'],
    world_model_changed=False,camera_fov_changed=False,runtime_tested=False),indent=2),encoding='utf-8')
print('STEEL_ARMET_WIDE_VISOR_PUBLISHED',flush=True)
