"""Save the three repaired torso meshes into isolated UE packages."""
import gc,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailTorsoRepair20261021'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailTorsoRepair20261021'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End PIE before saving torso assets')
io=module('mail_torso_save','Tools/GarmentSleeveRepair/save_assets.py')
io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
io.receipt['completed']=False;io.record()
for profile in ('Body','Jason','Owner_Jason'):
    path=R/'Authored/ue_chainmail_shirt'/(profile+'.json')
    io.write_mesh(dict(profile=profile,item='ue_chainmail_shirt',file=str(path)))
    gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=True;io.record()
print('CHAINMAIL_TORSOS_SAVED',flush=True)
