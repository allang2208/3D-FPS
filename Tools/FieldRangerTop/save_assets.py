"""Save four native ranger garments per serialized batch."""
import gc, hashlib, importlib.util, json, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020'
spec=importlib.util.spec_from_file_location('ranger_material_assets',str(P/'Tools/FieldRangerTop/materials.py'))
materials=importlib.util.module_from_spec(spec);spec.loader.exec_module(materials)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving ranger clothing')
spec=importlib.util.spec_from_file_location('ranger_mesh_io',str(P/'Tools/GarmentSleeveRepair/save_assets.py'))
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
io.R=R;io.DEST=materials.DEST;io.receipt_path=R/'saved_assets.json'
io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
manifest=read(R/'authored.json')
if not manifest['completed']:raise RuntimeError('Complete ranger authoring before saving')
base=materials.create();io.receipt['completed']=False;io.record()
rows=[r for r in manifest['records'] if io.receipt['saved'].get('ue_field_sweater/'+r['profile'],{}).get('author_sha256')!=hashlib.sha256(Path(r['authored']).read_bytes()).hexdigest()]
for row in rows[:4]:
    io.R=Path(row['authored']).parents[2]
    io.DEST=materials.DEST+('/CollarRepair20261021' if io.R.name=='CollarRepair20261021' else '')
    d=read(row['authored']);skin=base[2]
    if row['profile']=='Body':skin=u.load_asset(row['source']).materials[4].material_interface
    mats=base+[skin]
    if row['group']=='Owner':mats=mats+mats
    desc=R/'SaveInputs'/(row['profile']+'.json');desc.parent.mkdir(parents=True,exist_ok=True)
    desc.write_text(json.dumps(dict(materials=[m.get_path_name() for m in mats],material_slots=d['material_slots'])),encoding='utf-8')
    io.write_mesh(dict(profile=row['profile'],item='ue_field_sweater',file=str(desc)))
    gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=len(rows)<=4;io.record()
print('RANGER_NATIVE_BATCH',len(io.receipt['saved']),len(manifest['records']),'complete='+str(io.receipt['completed']),flush=True)
