import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'V03/Authoring/FacelessReceptionist_V03.blend'))
rig=bpy.data.objects['root'];s=bpy.context.scene
names=[b.name for b in rig.data.bones]
report={'bones':names,'clips':{}}
for role in ['idle','walk','attack']:
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=str(ROOT/'MotionSources'/('A_Receptionist_'+role+'.fbx')),use_anim=True)
 imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
 first,last=map(int,donor.animation_data.action.frame_range)
 world=donor.matrix_world.copy();inv={n:(world@donor.data.bones[n].matrix_local).inverted() for n in names}
 frames=list(range(first,last+1));matrices=[];joints=[]
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update()
  matrices.append([np.asarray(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
  joints.append({n:list(donor.matrix_world@donor.pose.bones[n].head) for n in ['pelvis','thigh_l','thigh_r','calf_l','calf_r','upperarm_l','upperarm_r']})
 np.savez_compressed(ROOT/'MotionSources'/('deform_'+role+'.npz'),matrices=np.asarray(matrices),names=np.array(names))
 report['clips'][role]={'frames':len(frames),'start_frame':first,'end_frame':last,'fps':float(s.render.fps)/s.render.fps_base,'joints':joints}
 for o in imported:bpy.data.objects.remove(o,do_unlink=True)
raw=list(rig['source_world_matrix']);world=Matrix([raw[i:i+4] for i in range(0,16,4)])
report['rest_heads']={n:list(world@rig.data.bones[n].head_local) for n in names}
report['rest_tails']={n:list(world@rig.data.bones[n].tail_local) for n in names}
(ROOT/'MotionSources/motion_frames.json').write_text(json.dumps(report),encoding='utf-8')
print('V04_MOTION_SOURCE_SAVED',[(r,d['frames']) for r,d in report['clips'].items()])
