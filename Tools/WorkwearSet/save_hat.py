import sys,importlib.util
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
path=P/'Tools/FieldHat/save_assets.py';spec=importlib.util.spec_from_file_location('workwear_hat_save',str(path));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.SRC=R/'Hat';h.DEST=DEST+'/Hat';h.receipt_path=R/'Hat/saved_assets.json';h.receipt=read(h.receipt_path) if h.receipt_path.exists() else dict(runtime_tested=False)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Do not save during PIE')
h.receipt['completed']=False;h.record();d=read(R/'Hat/Authored/hat.json');mats=h.create_materials(h.texture_assets());h.receipt['materials']=[m.get_path_name() for m in mats];h.record();mesh=h.skeletal(mats,d);fits=h.imported_fits(mesh,d);h.displays(mats,d)
h.receipt.update(completed=True,source_triangles=len(d['triangles']),fit=fits,tip_bones=['BrimBackBase','BrimBackMid','BrimBackEnd'],runtime_tested=False);h.record();print('WORKWEAR_HAT_ASSETS_SAVED',flush=True)
