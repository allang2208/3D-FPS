import bpy,json
from pathlib import Path
from mathutils import Vector
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend')
rig=bpy.data.objects['SK_AKM_Viewmodel']
report={'rig_matrix':[list(r) for r in rig.matrix_world], 'meshes':[], 'bones':[],'samples':[]}
for o in bpy.data.objects:
    if o.type=='MESH' and o.parent==rig:
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'bounds':[[min(v[i] for v in pts),max(v[i] for v in pts)]for i in range(3)],'matrix':[list(r) for r in o.matrix_world],'groups':[g.name for g in o.vertex_groups]})
for b in rig.data.bones:
    if b.name.startswith('WPN_') or b.name.startswith('hand_'):
        report['bones'].append({'name':b.name,'parent':b.parent.name if b.parent else None,'head_world':list(rig.matrix_world@b.head_local),'rest_matrix':[list(r) for r in b.matrix_local]})
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=900;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.world.color=(.05,.05,.05)
camera_data=bpy.data.cameras.new('ReferenceCamera');camera=bpy.data.objects.new('ReferenceCamera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
camera_data.lens=48
light_data=bpy.data.lights.new('ReferenceLight','AREA');light_data.energy=100;light_data.size=2
light=bpy.data.objects.new('ReferenceLight',light_data);bpy.context.collection.objects.link(light)
for clip,frames in [('idle',[1]),('reload',[15,35,52,66]),('reload_empty',[52,75,88,96])]:
    action=bpy.data.actions['AKM_'+clip];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for f in frames:
        scene.frame_set(f);bpy.context.view_layer.update()
        report['samples'].append({'clip':clip,'frame':f,'time':(f-1)/24,'bones':{n:list((rig.matrix_world@rig.pose.bones[n].matrix).translation)for n in ['WPN_root','WPN_bolt','WPN_SOCKET_Magazine','hand_l','hand_r']}})
        pts=[];deps=bpy.context.evaluated_depsgraph_get()
        for o in bpy.data.objects:
            if o.type=='MESH' and o.parent==rig and not o.hide_render:
                e=o.evaluated_get(deps);m=e.to_mesh();pts.extend(e.matrix_world@v.co for v in m.vertices);e.to_mesh_clear()
        mn=Vector([min(p[i]for p in pts)for i in range(3)]);mx=Vector([max(p[i]for p in pts)for i in range(3)]);center=(mn+mx)*.5
        camera.location=center+Vector((.95,-1.25,.65));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        light.location=center+Vector((.5,-.2,1.4));light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/f'akm_replacement_reference_{clip}_{f:03d}.png');bpy.ops.render.render(write_still=True)
(OUT/'akm_replacement_reference_contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'meshes':report['meshes'],'bones':report['bones']},indent=2))
