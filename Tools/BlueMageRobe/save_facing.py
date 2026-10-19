"""Save corrected torso adornments without changing the hem/cloth recipe."""
import json,sys,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'FacingFix20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import save_assets as io
original=json.loads((R/'saved_assets.json').read_text());io.receipt_path=OUT/'saved_assets.json';io.receipt=json.loads(io.receipt_path.read_text()) if io.receipt_path.exists() else dict(saved={},runtime_tested=False,network_tested=False)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Preserve current PIE before saving robe facing repair')
io.receipt['completed']=False;io.record()
for profile in ('Body','Body_Owner','Jason','Jason_Owner'):
    io.skeletal(OUT/'Authored'/(profile+'.json'),[io.load(p) for p in original['materials'][profile.split('_')[0]]],True,revision='FacingFix20261020')
    io.receipt['saved']['Body/'+profile]['facing_revision']='20261020-native-forward-v1';io.record();gc.collect();u.SystemLibrary.collect_garbage()
io.displays([io.load(p) for p in original['materials']['Jason']])
sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'));from save_icons import apply_item
apply_item('ue_blue_mage_robe')
io.receipt['completed']=True;io.receipt['cloth_revision']=io.CLOTH_REVISION;io.receipt['facing_revision']='20261020-native-forward-v1';io.receipt['icon_png_unchanged']=True;io.record();print('ROBE_FACING_ASSETS_SAVED 4',flush=True)
