import bpy,json,math
from pathlib import Path
from mathutils import Vector
out=Path(r'D:\FPS3D\FPSGAME\Saved\NurseZombie')
report=[]
for clip, samples in [('Idle05',[0,2.5,5,7.5]),('Walk01Forward',[0,.8,1.6,2.4]),('AttackForward05',[0,.4,.8,1.2,1.6,2,2.4,3.2])]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(out/('ANMS_ZombieFemale'+clip+'.fbx')))
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=440;scene.render.resolution_y=500;scene.render.resolution_percentage=100
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.6,.64,.66)
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.world=bpy.data.worlds.new('World');scene.world.color=(.08,.08,.08)
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    action=rig.animation_data.action
    report.append({'clip':clip,'frames':list(action.frame_range),'fps':scene.render.fps,'bones':[b.name for b in rig.pose.bones],'root_samples':[]})
    data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=2.4
    cam.location=(3,-5,2);cam.rotation_euler=(Vector((0,0,1))-cam.location).to_track_quat('-Z','Y').to_euler()
    for t in samples:
        scene.frame_set(round(t*scene.render.fps)+1);bpy.context.view_layer.update()
        meshes=[o for o in scene.objects if o.type=='MESH']
        pts=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
        if pts:
            c=Vector([(min(p[i] for p in pts)+max(p[i] for p in pts))*.5 for i in range(3)])
            cam.location=c+Vector((3,-5,1));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
        report[-1]['root_samples'].append({'t':t,'root':list((rig.matrix_world@rig.pose.bones[0].matrix).translation),'hand_l':list((rig.matrix_world@rig.pose.bones['hand_l'].matrix).translation),'hand_r':list((rig.matrix_world@rig.pose.bones['hand_r'].matrix).translation)})
        scene.render.filepath=str(out/(clip+'_'+str(t)+'.png'));bpy.ops.render.render(write_still=True)
(out/'source-motion.json').write_text(json.dumps(report,indent=2))
print('NURSE_SOURCE_RENDER_OK')
