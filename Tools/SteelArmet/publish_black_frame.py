"""Publish the saved procedural visor after the native material consumer is built."""
import hashlib, importlib.util, json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SteelArmet20261019/BlackFrame20261020'
saved=json.loads((R/'saved_assets.json').read_text())
revision=hashlib.sha256((P/'Tools/SteelArmet/black_frame.hlsl').read_text().encode()+
    (P/'Tools/SteelArmet/save_black_frame.py').read_bytes()).hexdigest()
if not saved.get('completed') or saved['revision']!=revision:raise RuntimeError('Save the current black frame first')
spec=importlib.util.spec_from_file_location('black_frame_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'))
entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
path=P/'Content/ColdSteelData/player_body.json';raw=path.read_bytes();text=raw.decode('utf-8-sig')
key=['head_equipment','ue_steel_armet','first_person_overlay']
previous=json.loads(text)['head_equipment']['ue_steel_armet']['first_person_overlay']
text=entries.replace(text,key,saved['material'])
if path.read_bytes()!=raw:raise RuntimeError('Body configuration changed during publication; retry')
backup=R/'publication-before.json'
if not backup.exists():backup.write_bytes(raw)
entries.commit_player_body(path,raw,text,owned_paths=[tuple(key)],producer=__file__)
(R/'published.json').write_text(json.dumps(dict(completed=True,previous_overlay=previous,
    overlay=saved['material'],world_model_changed=False,camera_fov_changed=False,
    runtime_tested=False),indent=2),encoding='utf-8')
print('HELMET_BLACK_FRAME_PUBLISHED',flush=True)
