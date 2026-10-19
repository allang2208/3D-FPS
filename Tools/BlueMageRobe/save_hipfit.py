"""Rebuild all four fitted robe cloth bodies and finish the authorized icon saves."""
import json,sys,gc,importlib.util
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'HipFit20261019';sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import save_assets as io
original=json.loads((R/'saved_assets.json').read_text());io.receipt_path=OUT/'saved_assets.json';io.receipt=json.loads(io.receipt_path.read_text()) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
def physics(mesh):
    # SkeletalBodySetups is not exposed to UE Python. Record the saved links;
    # the scoped source-geometry comparison records the authored collider sizes.
    asset=mesh.get_editor_property('physics_asset');cloths=[]
    for cloth in mesh.get_editor_property('mesh_clothing_assets'):
        linked=cloth.get_editor_property('physics_asset')
        cloths.append(dict(asset=cloth.get_path_name(),physics_asset=linked.get_path_name() if linked else None))
    return dict(mesh_physics_asset=asset.get_path_name() if asset else None,clothing_assets=cloths,shape_readback='not exposed to UE Python')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Preserve current PIE before robe body authoring')
io.receipt['completed']=False;io.record();before={}
for profile in ('Body','Body_Owner','Jason','Jason_Owner'):
    old=original['saved']['Body/'+profile]['asset'];before[profile]=physics(io.load(old))
    io.skeletal(R/'Authored/Body'/(profile+'.json'),[io.load(p) for p in original['materials'][profile.split('_')[0]]],True,revision='HipFit20261019')
    row=io.receipt['saved']['Body/'+profile];mesh=io.load(row['asset']);row['physics_asset_binding']=physics(mesh);row['hip_fit_revision']='20261019-v1';io.record();gc.collect();u.SystemLibrary.collect_garbage()
(OUT/'collision-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
io.displays([io.load(p) for p in original['materials']['Jason']])
path=P/'Tools/BlueMageSetIcons/save_icons.py';spec=importlib.util.spec_from_file_location('mage_set_hipfit_icon_save',str(path));icons=importlib.util.module_from_spec(spec);spec.loader.exec_module(icons)
for key in icons.FAMILIES:icons.apply_item(key)
io.receipt['completed']=True;io.receipt['hip_fit_revision']='20261019-v1';io.record();print('BLUE_ROBE_HIPFIT_AND_ICONS_SAVED',flush=True)
