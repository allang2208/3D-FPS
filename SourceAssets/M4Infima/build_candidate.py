import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima');src=out/'Original/Blender_Source_Files_FreeFpsTemplate'
bpy.ops.wm.open_mainfile(filepath=str(src/'Animations/Animations_Assault_Rifle.blend'))
scene=bpy.context.scene;arm=next(o for o in scene.objects if o.name=='Armature');gun=next(o for o in scene.objects if o.name=='SKEL_AssaultRifle')
for image in bpy.data.images:
 candidate=next(iter(src.rglob(Path(image.filepath.replace('\\','/')).name)),None)
 if candidate:
  try:image.filepath=str(candidate);image.reload()
  except Exception:pass
for o in scene.objects:
 if o.type=='MESH' and o.name!='SK_Manny_Arms':o.hide_render=True
with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/M4_Assembled_Candidate.blend',link=False)as(a,b):b.objects=[n for n in a.objects]
for o in b.objects:
 if o.type=='MESH':scene.collection.objects.link(o)
bpy.context.view_layer.update()
fit=Matrix(((100,0,0,-3.7),(0,100,0,-16),(0,0,100,4),(0,0,0,1)))
for o in b.objects:
 if o.type!='MESH':continue
 o.data.transform(fit@o.matrix_world);o.parent=gun;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
 g=o.vertex_groups.new(name='Magazine' if o.name.startswith('Magazine') else 'Trigger' if o.name.startswith('Trigger') else 'Grip');g.add(list(range(len(o.data.vertices))),1,'REPLACE')
 m=o.modifiers.new('M4Rig','ARMATURE');m.object=gun;o.hide_render=False
 o.name='M4_'+o.name
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=750;scene.render.resolution_percentage=100
for co in [(100,0,240),(-100,-80,190)]:
 d=bpy.data.lights.new('M4Review','AREA');d.energy=1500000;d.size=150;o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);o.location=co;o.rotation_euler=(Vector((0,-20,150))-o.location).to_track_quat('-Z','Y').to_euler()
for clip,frames in [('Idle_Pose',[0]),('Reload',[0,15,30,45,60,80]),('Aim_Pose',[0])]:
 a=bpy.data.actions['A_FP_AssaultRifle_'+clip];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
 w=bpy.data.actions['A_FP_WEP_AssaultRifle_Reload' if clip=='Reload' else 'A_WEP_Reference'];gun.animation_data.action=w;gun.animation_data.action_slot=w.slots[0]
 for f in frames:
  scene.frame_set(f);bpy.context.view_layer.update();scene.render.filepath=str(out/('fit_'+clip+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'M4_Infima_Candidate.blend'))
