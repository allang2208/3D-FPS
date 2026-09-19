import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'hunyuan_v01'));import studio
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
bpy.ops.import_scene.fbx(filepath=str(R/'delivery/SK_HandBrain_FiveActions.fbx'))
s=bpy.context.scene;rig=next(o for o in s.objects if o.type=='ARMATURE');a=next(a for a in bpy.data.actions if a.name.endswith('Death'))
rig.animation_data.action=a
if a.slots:rig.animation_data.action_slot=a.slots[0]
actions={a.name:(a.frame_range[1]-a.frame_range[0])/30 for a in bpy.data.actions}
assert len(actions)==5 and abs((a.frame_range[1]-a.frame_range[0])/30-2.8)<1e-5
body=bpy.data.objects['HandBrain_Body'];heights=[];pose=[];root=[]
for f in range(1,86):
 s.frame_set(f);bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 coords=np.array([e.matrix_world@v.co for v in m.vertices]);e.to_mesh_clear();assert np.isfinite(coords).all();heights.append(float(coords[:,2].min()))
 root.append(np.array(rig.pose.bones['root'].matrix))
 if f in [64,85]:pose.append(coords)
assert min(heights)>-.002,(min(heights),max(heights))
settled=float(np.max(np.abs(pose[1]-pose[0])));assert settled<1e-5,settled
rooterror=max(float(np.max(np.abs(x-root[0]))) for x in root);assert rooterror<1e-5
(R/'delivery/fbx_validation.json').write_text(json.dumps({'actions':actions,'floor_min_m':min(heights),'floor_max_m':max(heights),'settled_pose_error':settled,'root_motion_error':rooterror,'ue_runtime_verified':False},indent=2))
cam=studio.setup(640);s.cycles.samples=16;cam.data.ortho_scale=3.35;studio.aim(cam,(6,-3,2.8),(.1,-.55,.8))
folder=R/'preview_frames';folder.mkdir(exist_ok=True)
for f,name in [(1,'standing'),(35,'impact'),(85,'corpse')]:
 s.frame_set(f);s.render.filepath=str(R/'delivery'/f'Death_{name}.png');bpy.ops.render.render(write_still=True)
for i in range(42):
 s.frame_set(1+i*2);s.render.filepath=str(folder/f'{i:03}.png');bpy.ops.render.render(write_still=True)
print('DEATH_FBX_AND_PREVIEW_COMPLETE')
