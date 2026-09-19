import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima');bpy.ops.wm.open_mainfile(filepath=str(out/'M4_Infima_Candidate.blend'))
s=bpy.context.scene;s.unit_settings.scale_length=1;arm=next(o for o in s.objects if o.name=='Armature');gun=next(o for o in s.objects if o.name=='SKEL_AssaultRifle');cam=s.camera
clips={'idle':('Idle_Loop',0,90),'aim':('Aim_Pose',0,1),'fire':('Fire',0,23),'aim_fire':('Fire_Aimed',0,23),'reload':('Reload',0,94),'reload_empty':('Reload',0,94),'equip':('Equip',0,31),'inspect':('Idle_Loop',0,90)}
def pose(clip,f):
 a=bpy.data.actions['A_FP_AssaultRifle_'+clip];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
 w=bpy.data.actions['A_FP_WEP_AssaultRifle_Reload' if clip=='Reload' else 'A_FP_WEP_AssaultRifle_Fire' if clip.startswith('Fire') else 'A_WEP_Reference'];gun.animation_data.action=w;gun.animation_data.action_slot=w.slots[0];s.frame_set(f+1);s.frame_set(f);bpy.context.view_layer.update()
pose('Idle_Pose',0)
# Source units are centimetres. Preserve the source camera coordinate frame at idle.
camera=cam.matrix_world.normalized();camera.translation=cam.matrix_world.translation
T=Matrix(((.01,0,0,0),(0,0,-.01,0),(0,.01,0,0),(0,0,0,1)))@camera.inverted()
names=[b.name for b in arm.data.bones if b.use_deform and not b.name.startswith(('CB_','REF_'))]
gmap={'Grip':'WPN_root','Magazine':'WPN_SOCKET_Magazine','Trigger':'WPN_Trigger','Bolt':'WPN_bolt'}
fit=Matrix(((100,0,0,-3.7),(0,100,0,-16),(0,0,100,4),(0,0,0,1)))
anchors={'WPN_RearSight':(.0369618,.1246755,.092796),'WPN_FrontSight':(.0369144,-.1887776,.0925183),'WPN_SOCKET_Muzzle':(.037,-.29,.032),'WPN_SOCKET_Eject':(.063,.08,.045)}
def matrices():
 d={n:T@arm.matrix_world@arm.pose.bones[n].matrix for n in names}
 d.update({n:T@gun.matrix_world@gun.pose.bones[b].matrix for b,n in gmap.items()})
 for n,p in anchors.items():d[n]=T@gun.matrix_world@gun.pose.bones['Grip'].matrix@gun.data.bones['Grip'].matrix_local.inverted()@Matrix.Translation(fit@Vector(p))
 # Strip scale from pose matrices; uniform unit conversion applies to translations only.
 for n,m in d.items():d[n]=Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((1,1,1)))
 return d
# Reference matrices must match original armature bind, not animated idle.
rest={n:T@arm.matrix_world@arm.data.bones[n].matrix_local for n in names}
rest.update({n:T@gun.matrix_world@gun.data.bones[b].matrix_local for b,n in gmap.items()})
rest.update({n:matrices()[n] for n in anchors})
for n,m in rest.items():rest[n]=Matrix.LocRotScale(m.translation,m.to_quaternion(),Vector((1,1,1)))
rigdata=bpy.data.armatures.new('M4Infima');rig=bpy.data.objects.new('SK_M4_Infima',rigdata);s.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for n,m in rest.items():b=rigdata.edit_bones.new(n);b.length=.025;b.matrix=m
bpy.ops.object.mode_set(mode='OBJECT')
# A single explicit root avoids multiple-root UE imports. Bake every source bone in model space.
bpy.ops.object.mode_set(mode='EDIT');r=rigdata.edit_bones.new('VM_Root');r.head=(0,0,0);r.tail=(0,0,.02)
for b in rigdata.edit_bones:
 if b.name!='VM_Root':b.parent=r
bpy.ops.object.mode_set(mode='OBJECT')
for im in bpy.data.images:
 candidate=next(iter((out/'Original').rglob(Path(im.filepath.replace(chr(92),'/')).name)),None)
 if candidate:im.filepath=str(candidate)
meshes=[]
for o in list(s.objects):
 if o.type!='MESH' or (o.name!='SK_Manny_Arms' and not o.name.startswith('M4_')):continue
 c=bpy.data.objects.new(o.name+'_Export',o.data.copy());s.collection.objects.link(c)
 for g in o.vertex_groups:c.vertex_groups.new(name=g.name)
 c.data.transform(T@o.matrix_world)
 c.parent=rig;c.matrix_parent_inverse=Matrix.Identity(4);c.matrix_basis=Matrix.Identity(4)
 for mod in list(c.modifiers):c.modifiers.remove(mod)
 for con in list(c.constraints):c.constraints.remove(con)
 for g in c.vertex_groups:
  if g.name in gmap:g.name=gmap[g.name]
 mod=c.modifiers.new('OriginalSkin','ARMATURE');mod.object=rig;c.hide_render=False;c.hide_set(False);meshes.append(c)
reports=[]
for key,(clip,start,end) in clips.items():
 rig.animation_data_create();action=bpy.data.actions.new('M4_'+key);action.use_fake_user=True;rig.animation_data.action=action
 for frame in range(start,end+1):
  pose(clip,frame)
  for n,m in matrices().items():
   b=rig.pose.bones[n];b.rotation_mode='QUATERNION';b.matrix_basis=b.bone.matrix_local.inverted()@m
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=frame-start)
 s.render.fps=30;s.frame_start=0;s.frame_end=end-start
 bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(out/('A_AKM_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True)
 reports.append({'clip':key,'duration':(end-start)/30,'source':clip,'frames':end-start+1})
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in meshes:o.select_set(True)
s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
bpy.ops.export_scene.fbx(filepath=str(out/'SK_M4_Infima.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE')
(out/'export_report.json').write_text(json.dumps({'clips':reports,'bones':len(rest)+1,'meshes':[o.name for o in meshes],'inspect':'idle placeholder; source has no inspect clip','empty_reload':'uses source reload; source has no dedicated empty variant'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'SK_M4_Infima_Export.blend'))







