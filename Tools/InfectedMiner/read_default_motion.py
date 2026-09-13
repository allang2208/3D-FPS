"""Read donor rest frames and action timing for the retarget operation."""
import bpy,json,sys
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
bpy.ops.wm.read_factory_settings(use_empty=True)
name=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'A_Mannequin_Axe_Act'
bpy.ops.import_scene.fbx(filepath=str(R/'Reference'/f'{name}.fbx'),anim_offset=0)
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
a=r.animation_data.action;s=bpy.context.scene
report={'rig':r.name,'matrix':list(map(list,r.matrix_world)),'fps':s.render.fps,'range':list(a.frame_range),'bones':{b.name:{'head':list(r.matrix_world@b.head_local),'tail':list(r.matrix_world@b.tail_local),'rotation':list((r.matrix_world@b.matrix_local).to_quaternion())} for b in r.data.bones},'poses':[]}
for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1,3):
 s.frame_set(f);bpy.context.view_layer.update()
 report['poses'].append({'frame':f,'bones':{n:{'p':list(r.matrix_world@r.pose.bones[n].head),'q':list((r.matrix_world@r.pose.bones[n].matrix).to_quaternion())} for n in ['pelvis','head','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','foot_l','foot_r']}})
(R/'Reference'/f'{name}-motion.json').write_text(json.dumps(report,indent=2))
print('SOURCE_MOTION '+json.dumps({'name':name,'fps':s.render.fps,'range':list(a.frame_range),'poses':[{'frame':p['frame'],'left':p['bones']['hand_l']['p'],'right':p['bones']['hand_r']['p'],'head':p['bones']['head']['p']} for p in report['poses']]}))
