"""Save a separate V8 sequence; never replace the backed-up V7 package."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the active play session; animation saving requires it to end')
DEST='/Game/Weapons/SteelWarhammer20261014/QuickReferenceV8'
NAME='A_Warhammer_QuickReferenceV8'
OWNER='WarhammerQuickReference20261107'
data=json.loads((P/'motion.json').read_text());frames=data['frames']
lib=u.EditorAssetLibrary
exists=lib.does_asset_exist(DEST+'/'+NAME)
if exists:
    seq=u.load_asset(DEST+'/'+NAME)
    tag=lib.get_metadata_tag(seq,'HammerQuick.Author')
    # This session created the package during PIE; UE accepted track writes
    # but rejected metadata/save. User shutdown subsequently saved that same
    # package. Its exact pre-finalization copy is retained alongside the task.
    staged=(P/'StagedDuringShutdown/A_Warhammer_QuickReferenceV8.uasset').exists() and not tag
    if tag!=OWNER and not staged:raise RuntimeError('Unowned existing asset')
    if any(p.get_name()==DEST+'/'+NAME for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved editor changes')
else:
    factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',u.load_asset(data['skeleton']))
    seq=u.AssetToolsHelpers.get_asset_tools().create_asset(NAME,DEST,u.AnimSequence,factory)
    if not seq:raise RuntimeError('Animation creation failed')
ctl=seq.get_editor_property('controller');ctl.open_bracket('Author hammer reference butt strike V8',False)
try:
    ctl.set_frame_rate(u.FrameRate(data['fps'],1),False)
    ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
    for bone in frames[0]:
        if not exists:ctl.add_bone_curve(bone,False)
        keys=[f[bone] for f in frames]
        if not ctl.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
            [u.Quat(*k['q'][1:],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
            raise RuntimeError('Track write failed '+bone)
finally:ctl.close_bracket(False)
seq.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
seq.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
seq.set_editor_property('enable_root_motion',False)
if not exists:u.AnimationLibrary.add_animation_notify_track(seq,'QuickStrikeTiming')
u.AnimationLibrary.remove_all_animation_sync_markers(seq)
for name,time in data['markers']:u.AnimationLibrary.add_animation_sync_marker(seq,name,time,'QuickStrikeTiming')
for key,value in {'Author':OWNER,'Reference':'_5pAl232f38 54-57s; active 55.65-56.95s',
    'Acceptance':'PendingUserReview','Previous':'QuickCombatLeftWristV7','Strike':'Shaft butt'}.items():
    lib.set_metadata_tag(seq,'HammerQuick.'+key,value)
if not lib.save_loaded_asset(seq,False):raise RuntimeError('Animation save failed')
(P/'saved-assets.json').write_text(json.dumps(dict(asset=seq.get_path_name(),frames=len(frames),
    fps=data['fps'],seconds=1.3,saved=True,runtime_tested=False),indent=2))
print('HAMMER_REFERENCE_SAVED',seq.get_path_name())
