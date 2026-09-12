import bpy,json,math,sys
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912')
source=R/('Candidates/CMU02_07' if '--cmu' in sys.argv else 'Delivery')
bpy.ops.wm.open_mainfile(filepath=str(source/'InfectedMiner_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['MinerRig'];a=bpy.data.actions['A_Miner_Attack'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
names=['pelvis','spine_03','head','upperarm_l','lowerarm_l','hand_l']
def poses(r):
    out={}
    for f in [1,12,24,36,46,54,67]:
        s.frame_set(f);bpy.context.view_layer.update();out[f]={n:r.matrix_world@r.pose.bones[n].matrix for n in names}
    return out
original=poses(r)
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.ops.import_scene.fbx(filepath=str(source/'A_Miner_Attack.fbx'),anim_offset=0.0);r=next(o for o in s.objects if o.type=='ARMATURE');roundtrip=poses(r)
report={'range':list(r.animation_data.action.frame_range),'frames':{}}
for f in original:
    report['frames'][f]={n:{'position_cm':100*(original[f][n].translation-roundtrip[f][n].translation).length,'angle_deg':math.degrees(original[f][n].to_quaternion().rotation_difference(roundtrip[f][n].to_quaternion()).angle)} for n in names}
print('ROUNDTRIP_POSE '+json.dumps(report),flush=True)
(R/('Previews/FBX_CMU' if '--cmu' in sys.argv else 'Previews/FBX')/'attack-pose-roundtrip.json').write_text(json.dumps(report,indent=2))
assert max(v['position_cm'] for row in report['frames'].values() for v in row.values())<.01
assert max(v['angle_deg'] for row in report['frames'].values() for v in row.values())<.1
