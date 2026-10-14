"""Read saved Kwang grip assets and compressed poses without starting a game."""
import json
import math
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonSwordGrip20261007'
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
saved=json.loads((OUT/'assets-saved.json').read_text())
source=json.loads((OUT/'adapted-actions.json').read_text())
mesh=u.load_asset(source['mesh'])
opt=u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh=mesh
opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
names=source['names']
keys=['Uppercut','Overhead','DashOverhead','Whirlwind.Start','Whirlwind.Loop','Whirlwind.End']
receipt=dict(pie_active=bool(u.EditorLevelLibrary.get_pie_worlds(True)),clips={})
poses=dict(mesh=source['mesh'],names=names,clips={})
for label in keys:
    path=saved['clips']['Melee.FullBody.'+label]
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing referenced animation: '+path)
    times,values=u.AnimationLibrary.get_float_keys(clip,'SwordGripRoll')
    markers=[str(m.marker_name) for m in u.AnimationLibrary.get_animation_sync_markers(clip)]
    c=source['clips'][label];frames=[];curve=[]
    count=2*(len(c['frames'])-1)+1
    for i in range(count):
        t=clip.get_play_length()*i/(count-1)
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
        frame=[]
        for bone in names:
            v=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
            frame.append([v.translation.x,v.translation.y,v.translation.z,v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w,v.scale3d.x,v.scale3d.y,v.scale3d.z])
        frames.append(frame)
        curve.append(u.AnimPoseExtensions.get_curve_weight(pose,'SwordGripRoll'))
    receipt['clips'][label]=dict(asset=path,duration=clip.get_play_length(),curve_keys=len(values),markers=markers,
        sampling_rate=str(clip.get_editor_property('platform_target_frame_rate').get_editor_property('default')),
        skeleton_matches=clip.get_editor_property('skeleton')==mesh.skeleton,curve_start=float(values[0]),curve_end=float(values[-1]),
        source_hash_matches=u.EditorAssetLibrary.get_metadata_tag(clip,'GripSourceHash')==saved['source_hash'],
        compressed_curve_key_error=max(abs(a-b) for a,b in zip(curve[::2],values)))
    assert receipt['clips'][label]['skeleton_matches'],label+' skeleton mismatch'
    assert receipt['clips'][label]['source_hash_matches'],label+' stale asset revision'
    assert {'Contact','Release','NativeSwordGrip'}.issubset(markers),label+' missing markers'
    assert len(values)==len(c['frames']),label+' missing curve keys'
    poses['clips'][label]=dict(frames=frames,rate=c['rate']*2,curves={'SwordGripRoll':curve})
    print('KWANG_ASSET_READ '+label)
(OUT/'asset-readback.json').write_text(json.dumps(receipt,indent=2))
(OUT/'compressed-poses.json').write_text(json.dumps(poses,separators=(',',':')))
print('KWANG_ASSET_AUDIT '+json.dumps(receipt))
assert all(c['compressed_curve_key_error']<.02 for c in receipt['clips'].values()),'compressed curve drift; see asset-readback.json'
