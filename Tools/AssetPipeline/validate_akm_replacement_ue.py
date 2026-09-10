"""Read back saved candidate assets in a separate UE process; never changes a level."""
import json,math
from pathlib import Path
import unreal
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
DEST='/Game/Weapons/AKMReplacement'
contract=json.loads((OUT/'akm_replacement_export_report.json').read_text())
mesh=unreal.load_asset(DEST+'/SK_AKM_Replacement');assert mesh
skeleton=mesh.get_editor_property('skeleton');assert skeleton
materials=[slot.get_editor_property('material_interface').get_path_name()for slot in mesh.get_editor_property('materials')]
assert all('_PBR.'in p for p in materials),materials
rows=[];max_loc=0;max_rot=0
bones=['VM_Root','root','hand_l','hand_r','WPN_root','WPN_bolt','WPN_magazine']
def vec(v):return [v.x,v.y,v.z]
def pose(animation,bone,frame):return unreal.AnimationLibrary.get_bone_pose_for_frame(animation,bone,frame,False)
for clip in contract['clips']:
    animation=unreal.load_asset(DEST+'/A_AKM_'+clip['clip']);assert animation
    assert animation.get_editor_property('skeleton')==skeleton,clip['clip']
    keys=animation.get_editor_property('number_of_sampled_keys')
    assert abs(animation.get_play_length()-clip['duration'])<.011
    row={'clip':clip['clip'],'duration':animation.get_play_length(),'sampled_keys':keys,'samples':{}}
    for f in sorted({0,(keys-1)//2,keys-1}):
        row['samples'][str(f)]={}
        for bone in bones+['WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Muzzle']:
            transform=pose(animation,bone,f)
            data={'translation':vec(transform.translation),'scale':vec(transform.scale3d)}
            assert all(math.isfinite(v)for vals in data.values()for v in vals),(clip['clip'],bone)
            row['samples'][str(f)][bone]=data
    if clip['source']=='unchanged source action':
        old=unreal.load_asset('/Game/Weapons/AKM/A_AKM_'+clip['clip'])
        for f in sorted({0,(keys-1)//2,keys-1}):
            for bone in bones:
                a=pose(old,bone,f);b=pose(animation,bone,f)
                loc=max(abs(x-y)for x,y in zip(vec(a.translation),vec(b.translation)))
                ra=a.rotation.rotator();rb=b.rotation.rotator()
                rot=max(abs(x-y)for x,y in zip([ra.roll,ra.pitch,ra.yaw],[rb.roll,rb.pitch,rb.yaw]))
                max_loc=max(max_loc,loc);max_rot=max(max_rot,rot)
    rows.append(row)
assert max_loc<.02,('Old action translation drift cm',max_loc)
assert max_rot<.1,('Old action rotation drift degrees',max_rot)
report={'passed':True,'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'material_slots':materials,
        'validation_context':globals().get('AKMR_VALIDATION_CONTEXT','Independent process saved asset readback'),
        'max_unchanged_translation_drift_cm':max_loc,'max_unchanged_euler_drift_degrees':max_rot,'clips':rows,
        'scope':'Shared skeleton, material bindings and sampled source pose parity. Live skin deformation/input acceptance remains separate.'}
(OUT/'akm_replacement_ue_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('AKM_REPLACEMENT_UE_VALIDATION_OK '+json.dumps({'max_cm':max_loc,'max_degrees':max_rot,'clips':len(rows),'slots':len(materials)}))
