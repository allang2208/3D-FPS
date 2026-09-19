import bpy,json,sys,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'hunyuan_v01'));import studio
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(R/'delivery/SK_HandBrain_SingleFace.fbx'))
s=bpy.context.scene;s.render.fps=30
rig=next(o for o in s.objects if o.type=='ARMATURE')
actions={}
for a in bpy.data.actions:
 for name,duration in [('Idle',2),('Move',1),('Attack_Slam',2),('Attack_Howl',3)]:
  if a.name.endswith(name):
   actual=(a.frame_range[1]-a.frame_range[0])/30;assert abs(actual-duration)<.001
   actions[name]={'action':a.name,'duration_s':actual}
assert len(actions)==4,actions
meshes=[o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
assert len(meshes)==4 and len(rig.data.bones)==37
a=bpy.data.actions[actions['Attack_Howl']['action']];rig.animation_data.action=a
if a.slots:rig.animation_data.action_slot=a.slots[0]
cam=studio.setup(640);cam.data.ortho_scale=2.65;studio.aim(cam,(5,-5,1.9),(.15,0,1.02))
for frame,state in [(1,'closed'),(40,'open'),(91,'end')]:
 s.frame_set(frame);s.render.filepath=str(R/'delivery'/('FBX_'+state+'.png'));bpy.ops.render.render(write_still=True)
(R/'delivery/fbx_validation.json').write_text(json.dumps({'actions':actions,'skinned_meshes':[o.name for o in meshes],'bones':len(rig.data.bones),'roundtrip_rendered':True,'ue_import_tested':False},indent=2))
print('SINGLE_FACE_FBX_VERIFIED')
