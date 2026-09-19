import unreal, json, math
from pathlib import Path
O=Path(__file__).parent
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
report={}
for clip,aligned,seat,length in [('reload',75,95,2.1),('reload_empty',53,80,148/60)]:
    asset=unreal.load_asset('/Game/Weapons/M4DrumDrop/Contact/A_M4_DrumContact_'+clip)
    assert asset and abs(asset.get_play_length()-length)<.0001
    opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
    opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED
    points=[]
    for k in range(aligned*16,seat*16+1):
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(asset,k/960,opt)
        root=unreal.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',unreal.AnimPoseSpaces.WORLD)
        mag=unreal.AnimPoseExtensions.get_bone_pose(pose,'WPN_SOCKET_Magazine',unreal.AnimPoseSpaces.WORLD)
        p=unreal.MathLibrary.inverse_transform_location(root,mag.translation)
        points.append((p.x,p.y,p.z))
    origin=points[0];d=[points[-1][i]-origin[i] for i in range(3)];norm=math.sqrt(sum(x*x for x in d));axis=[x/norm for x in d]
    maximum=0.
    for p in points:
        delta=[p[i]-origin[i] for i in range(3)];along=sum(delta[i]*axis[i] for i in range(3))
        maximum=max(maximum,math.sqrt(sum((delta[i]-along*axis[i])**2 for i in range(3))))
    report[clip]={'asset':asset.get_path_name(),'compressed_samples':len(points),'sample_hz':960,'straight_insertion_max_lateral_error_cm':maximum,'source_duration':asset.get_play_length()}
    assert maximum<.005,report
(O/'saved_validation.json').write_text(json.dumps(report,indent=2))
unreal.log('DRUM_CONTACT_SAVED_PASS '+json.dumps(report))
