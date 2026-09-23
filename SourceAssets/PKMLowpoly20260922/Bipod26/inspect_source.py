import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['PKM_Manny_Rig'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
dg=bpy.context.evaluated_depsgraph_get();report={}
for part in [65,72,127,128,129]:
    ob=bpy.data.objects[f'PKM_Part_{part:03d}'];ev=ob.evaluated_get(dg)
    mesh=bpy.data.meshes.new_from_object(ev,depsgraph=dg);mesh.transform(root.inverted()@ev.matrix_world)
    vertices=[v.co for v in mesh.vertices]
    report[str(part)]={'exported_with_body':'mechanical_bone' in ob,'attachment_id':ob.get('attachment_id'),
        'min':[min(p[k] for p in vertices) for k in range(3)],'max':[max(p[k] for p in vertices) for k in range(3)],
        'materials':[m.name for m in mesh.materials], 'vertices':len(vertices)}
    copy=bpy.data.objects.new('Bipod26_'+str(part),mesh);bpy.context.scene.collection.objects.link(copy)
    copy.color=(.2,.35,.6,1) if part in [127,128] else (.7,.4,.1,1)
for ob in bpy.context.scene.objects:ob.hide_render=not ob.name.startswith('Bipod26_')
s=bpy.context.scene;cd=bpy.data.cameras.new('BipodInspect');cam=bpy.data.objects.new('BipodInspect',cd);s.collection.objects.link(cam);s.camera=cam
center=Vector((0,-.51,.026));cam.location=center+Vector((.7,.2,.08));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=.45;cd.clip_start=.001
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100;s.render.filepath=str(O/'source_split.png');bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'SourceInspection.blend'))
(O/'source_inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
