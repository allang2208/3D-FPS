"""Publish only the left-arm tracks of the two live M24 bipod clips."""
from pathlib import Path
import gzip,hashlib,json
import unreal as u
O=Path(__file__).resolve().parent
E=u.EditorAssetLibrary
folder='/Game/Weapons/M24/Bipod20261029'
review_revision=globals().get('REVIEW_REVISION',False)
manifest=json.loads((O/('review_input_manifest.json' if review_revision else 'input_manifest.json')).read_text())
for path,expected in manifest.items():
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Target changed during authoring; retain newer work: '+path)
if any(p.get_name().startswith(folder) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved bipod assets retained')
with gzip.open(O/'authored.json.gz','rt',encoding='utf-8') as f:spec=json.load(f)
parents=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['parents']
def owned(n):
    if n=='ik_hand_l':return True
    while n:
        if n=='clavicle_l':return True
        n=parents.get(n)
    return False
receipt={'complete':False,'saved':[],'track_scope':'clavicle_l subtree and ik_hand_l only',
         'duration':spec['duration'],'runtime_tested':False,'rendered':False,'cpp_changed':False}
curves=json.loads((O/'elbow_curves.json').read_text()) if review_revision else {}
if curves:
    import shutil
    skel=u.load_asset(spec['mesh']).skeleton
    skel_path=skel.get_path_name().split('.')[0]
    if any(p.get_name()==skel_path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved skeleton retained')
    skel_file=O.parents[1]/'Content'/(skel_path.removeprefix('/Game/')+'.uasset')
    shutil.copy2(skel_file,O/'Review/Before/Assets'/skel_file.name)
    for n in curves:
        u.AnimationLibrary.add_curve_meta_data(skel,n,False)
        u.AnimationLibrary.set_curve_meta_data_morph_target(skel,n,True)
    if not E.save_loaded_asset(skel,False):raise RuntimeError('Morph curve metadata save failed')
    receipt['morph_curve_skeleton']=skel.get_path_name()
for family,entry in spec['clips'].items():
    clip=u.load_asset(folder+'/A_M24_Bipod_'+family)
    if not clip:raise RuntimeError('Missing live bipod clip '+family)
    model=clip.get_editor_property('data_model_interface');rate=model.get_frame_rate()
    # Keep non-owned tracks bit-for-bit in their existing data-model timing.
    if rate.numerator!=spec['rate']*rate.denominator or model.get_number_of_keys()!=len(entry['frames']):
        raise RuntimeError('Live bipod timing differs; preserve other tracks')
    ctl=clip.get_editor_property('controller');ctl.open_bracket('M24 natural bipod hand and elbow',False)
    try:
        for j,n in enumerate(spec['names']):
            if not owned(n):continue
            keys=[row[j] for row in entry['frames']]
            ctl.add_bone_curve(n,False)
            if not ctl.set_bone_track_keys(n,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):
                raise RuntimeError('Write failed '+n)
    finally:ctl.close_bracket(False)
    for n,c in curves.items():
        u.AnimationLibrary.add_curve(clip,n)
        u.AnimationLibrary.add_float_curve_keys(clip,n,c['times'],c['values'])
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression failed '+family)
    E.set_metadata_tag(clip,'BipodHandsRevision','HandElbow20261030; native hinge; V9 absolute twist; phased hook; 0.48s')
    E.set_metadata_tag(clip,'BipodHandsSource',str(O/'M24_Bipod_Hands_Editable.blend'))
    if not E.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+family)
    asset_file=O.parents[1]/'Content/Weapons/M24/Bipod20261029'/('A_M24_Bipod_'+family+'.uasset')
    receipt['saved'].append({'path':clip.get_path_name(),'sha256':hashlib.sha256(asset_file.read_bytes()).hexdigest()})
    (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True
receipt['rendered']=review_revision
receipt['offline_surface_review']=review_revision
receipt['elbow_curve_count']=len(curves)
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('M24_BIPOD_HAND_ELBOW_SAVED',json.dumps(receipt),flush=True)
