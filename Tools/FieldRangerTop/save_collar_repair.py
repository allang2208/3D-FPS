"""Save only Body, Jason and Owner_Jason to the isolated collar revision."""
import gc, hashlib, importlib.util, json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/FieldRangerTop20261020';R=BASE/'CollarRepair20261021'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/CollarRepair20261021'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving collar repair assets')
manifest=read(R/'authored.json')
if not manifest['completed']:raise RuntimeError('Collar authoring is incomplete')
io=module('collar_native_io','Tools/GarmentSleeveRepair/save_assets.py');io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json'
io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
io.receipt['completed']=False;io.record()
base=read(BASE/'materials.json')['materials']
for row in manifest['records']:
    d=read(Path(row['authored']));mats=base+[base[2]]
    if row['profile']=='Body':mats[-1]=u.load_asset(d['binding_source']).materials[4].material_interface.get_path_name()
    if row['profile']=='Owner_Jason':mats+=mats
    desc=R/'SaveInputs'/(row['profile']+'.json');desc.parent.mkdir(parents=True,exist_ok=True)
    desc.write_text(json.dumps(dict(materials=mats,material_slots=d['material_slots'])),encoding='utf-8')
    io.write_mesh(dict(profile=row['profile'],item='ue_field_sweater',file=str(desc)))
    del d;gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=True;io.record();print('COLLAR_NATIVE_SAVED',len(io.receipt['saved']),flush=True)
