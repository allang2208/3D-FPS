"""Save the apartment variants and six native takes, then apply targeted map edits."""
import json,runpy
from pathlib import Path
from datetime import datetime
import unreal as u
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
DEST='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV14'
# A later independently authored rest family now owns the live routes. Replaying
# this historical importer must not replace those animations or camera profiles.
live_body=json.loads((PROJECT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
newer_routes={k:v for k,v in live_body.get('clips',{}).items() if k.startswith('Rest.Apartment') and not v.startswith(DEST+'/')}
if newer_routes:raise RuntimeError('V14 rest import is superseded; preserve current Rest.Apartment routes and use install_level.py only for the scene layer.')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
before=json.loads((R/'layout_before.json').read_text(encoding='utf8'))
receipt=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else dict(meshes={},materials={},clips={})
def save_receipt():
    (R/'assets_saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())

for key,label,factor in [('Bed','AP_Bed2_Bed',1.4),('Sofa','AP_Living_Sofa',1.2)]:
    if key in receipt['meshes']:continue
    source=before[label]['components'][0];name='SM_AP14_'+key;path=DEST+'/Meshes/'+name
    mesh=u.load_asset(path) if E.does_asset_exist(path) else A.duplicate_asset(name,DEST+'/Meshes',u.load_asset(source['mesh']))
    if not mesh:raise RuntimeError('Furniture duplicate failed: '+key)
    mats=[]
    for i,p in enumerate(source['materials']):
        m=u.load_asset(p) if p else None
        if m and isinstance(m,u.MaterialInstanceConstant):
            uv=L.get_material_instance_scalar_parameter_value(m,'UVScale')
            if uv>0:
                name=f'MI_AP14_{key}_{i}';path=DEST+'/Materials/'+name
                m=u.load_asset(path) if E.does_asset_exist(path) else A.duplicate_asset(name,DEST+'/Materials',m)
                L.set_material_instance_scalar_parameter_value(m,'UVScale',uv*factor);L.update_material_instance(m);save(m)
        mats.append(m.get_path_name() if m else None)
    save(mesh);receipt['meshes'][key]=mesh.get_path_name();receipt['materials'][key]=mats;save_receipt()
    print('AP14_FURNITURE_SAVED',key)

d=json.loads((R/'authored.json').read_text());body=u.load_asset(d['mesh'])
factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',body.skeleton);factory.set_editor_property('preview_skeletal_mesh',body)
for role,data in d['clips'].items():
    if role in receipt['clips']:continue
    name='A_'+role.replace('.','_');path=DEST+'/Animations/'+name
    if E.does_asset_exist(path):raise RuntimeError('Unreceipted animation preserved: '+path)
    clip=A.create_asset(name,DEST+'/Animations',u.AnimSequence,factory)
    ctl=clip.get_editor_property('controller');frames=data['frames'];ctl.open_bracket('Apartment bedside contacts',False)
    try:
        ctl.set_frame_rate(u.FrameRate(30,1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for i,bone in enumerate(d['names']):
            ctl.add_bone_curve(bone,False);keys=[f[i] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError('Track failed: '+bone)
    finally:ctl.close_bracket(False)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation finalization failed '+role)
    save(clip);receipt['clips'][role]=clip.get_path_name();save_receipt();print('AP14_ANIMATION_SAVED',role)

path=PROJECT/'Content/ColdSteelData/player_body.json';raw=path.read_bytes();candidate=json.loads(raw.decode('utf-8-sig'))
candidate['clips'].update(receipt['clips'])
runpy.run_path(str(PROJECT/'Tools/PlayerBody/config_transaction.py'))['commit'](path,raw,candidate,owned_paths=[('clips',role) for role in receipt['clips']],producer=__file__)
# Separate apartment overlay leaves the concurrent global furniture family intact.
(PROJECT/'Content/ColdSteelData/apartment_furniture_rest.json').write_bytes((R/'apartment_furniture_rest.json').read_bytes())
runpy.run_path(str(R/'install_level.py'))['main']()
receipt.update(stage='assets_and_map_saved',saved_at=datetime.now().astimezone().isoformat());save_receipt()
print('AP14_COMPLETED',len(receipt['clips']))
