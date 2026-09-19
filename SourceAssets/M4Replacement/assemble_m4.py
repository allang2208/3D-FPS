import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(r'D:/FPS3D/FPSGAME/SourceAssets/M4Replacement')
bpy.ops.wm.open_mainfile(filepath=str(out/'m4_source_imported.blend'))
keep={'M4 Body','Grip Default Unreal','Handguard Kmode Unreal','Magazine Light.003','Stock Classic Unreal','Flash Hider Unreal','Trigger Straight Unreal'}
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name not in keep:bpy.data.objects.remove(o,do_unlink=True)
# Seat the optional flash hider on the selected Kmode barrel.
bpy.data.objects['Flash Hider Unreal'].location += Vector((0,.056,-.053))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type=='MESH':o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'M4_Assembled_Candidate.blend'))
bpy.ops.export_scene.fbx(filepath=str(out/'SM_M4_Assembled_Candidate.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('M4World');scene.world.color=(.13,.13,.13)
pts=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices]
center=(Vector([min(v[i] for v in pts)for i in range(3)])+Vector([max(v[i] for v in pts)for i in range(3)]))*.5
camdata=bpy.data.cameras.new('M4Review');cam=bpy.data.objects.new('M4Review',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.9
cam.location=center+Vector((1,-.1,.1));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for co in [(1,-1,2),(-1,1,1)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=200;d.size=2;o=bpy.data.objects.new('Review',d);bpy.context.collection.objects.link(o);o.location=center+Vector(co);o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'m4_assembled_candidate.png');bpy.ops.render.render(write_still=True)
print('M4_ASSEMBLED',sorted(keep))



