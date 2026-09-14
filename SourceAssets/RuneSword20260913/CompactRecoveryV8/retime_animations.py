"""Re-time accepted complete poses; keep the V6 sword path and arm solution."""
import bpy,json,math,sys
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from rhythm_clock import source_time,timing_description,ATTACK_END
OUT=P/'Export';OUT.mkdir(exist_ok=True)
source=P.parent/'DiagonalHeavyV6/AzureRunesword_Manny_Editable.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
s.render.fps=240;s.render.fps_base=1
source_actions={name:bpy.data.actions['A_RuneSword_'+name] for name in ['Slash1','Slash2']}
for name,action in source_actions.items():action.name='REF_V6_A_RuneSword_'+name
receipt=[]
for name,old in source_actions.items():
    r.animation_data.action=old;r.animation_data.action_slot=old.slots[0]
    frames=[]
    # Cache all local transforms before replacing the action. Every bone reads
    # the same source instant, preserving the two-hand grasp and elbow paths.
    for f in range(round(ATTACK_END*240)+1):
        at=source_time(f/240)*240;frame=math.floor(at)
        s.frame_set(frame,subframe=at-frame);bpy.context.view_layer.update()
        frames.append({b.name:(b.location.copy(),b.rotation_quaternion.copy(),b.scale.copy()) for b in r.pose.bones})
    action=bpy.data.actions.new('A_RuneSword_'+name);action.use_fake_user=True
    r.animation_data.action=action;s.frame_start=0;s.frame_end=len(frames)-1;previous={}
    for f,pose in enumerate(frames):
        s.frame_set(f)
        for b in r.pose.bones:
            loc,q,scale=pose[b.name]
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale;previous[b.name]=q.copy()
            b.keyframe_insert('location',frame=f,group=b.name);b.keyframe_insert('rotation_quaternion',frame=f,group=b.name);b.keyframe_insert('scale',frame=f,group=b.name)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_RuneSword_'+name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    receipt.append({'clip':name,'duration':ATTACK_END,'fps':240,'frames':len(frames),'source_action':old.name})
    print('RETIME_EXPORTED '+name,flush=True)
r.animation_data.action=bpy.data.actions['A_RuneSword_Idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=800;s.frame_set(0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
description=timing_description();description.update({'source':str(source),'clips':receipt,'retained':'V6 entire pose trajectory and blade alignment; V5 idle; meshes, materials and rift geometry unchanged'})
(P/'authoring.json').write_text(json.dumps(description,indent=2),encoding='utf-8')
print('RUNESWORD_V8_AUTHORED',flush=True)
