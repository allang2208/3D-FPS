"""Read raw and compressed UE poses at 120 Hz, including subframes."""
import unreal,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909')
BONES=['WPN_root','WPN_Trigger','WPN_SOCKET_Magazine','WPN_bolt','WPN_RearSight','WPN_FrontSight',
       'hand_r','hand_l','pinky_02_l','pinky_03_l','index_01_r','index_02_r','index_03_r']
report={}
for folder in ['M4InfimaV3','M4InfimaRigV4']:
    mesh=unreal.load_asset('/Game/Weapons/'+folder+'/SK_M4_Infima');assert mesh
    materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.materials]
    assert all(materials),materials
    report[folder]={'materials':materials,'clips':{}}
    for clip in ['idle','aim','fire','reload','reload_empty','equip']:
        a=unreal.load_asset('/Game/Weapons/'+folder+'/A_AKM_'+clip);assert a
        sample_count=round(a.get_play_length()*120)+1
        result={'duration':a.get_play_length(),'sample_rate':120}
        for key,kind in [('raw',unreal.AnimDataEvalType.RAW),('compressed',unreal.AnimDataEvalType.COMPRESSED)]:
            options=unreal.AnimPoseEvaluationOptions();options.evaluation_type=kind;options.optional_skeletal_mesh=mesh
            samples=[]
            for index in range(sample_count):
                pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,min(index/120,a.get_play_length()),options)
                assert unreal.AnimPoseExtensions.is_valid(pose),(folder,clip,key,index)
                sample={}
                for name in BONES:
                    t=unreal.AnimPoseExtensions.get_bone_pose(pose,name,unreal.AnimPoseSpaces.WORLD)
                    sample[name]={'p':[t.translation.x,t.translation.y,t.translation.z],
                                  'q':[t.rotation.w,t.rotation.x,t.rotation.y,t.rotation.z],
                                  's':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
                samples.append(sample)
            result[key]=samples
        report[folder]['clips'][clip]=result
(OUT/'ue_pose_validation.json').write_text(json.dumps(report,separators=(',',':')))
unreal.log('M4_RIG_UE_POSE_READBACK_PASS')
