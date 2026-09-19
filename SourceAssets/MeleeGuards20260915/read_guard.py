import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/MeshyMelee20260915/FrostCrystalSword_Manny_Editable.blend')
rig=bpy.data.objects['SK_RuneSword_Rig']
sword=bpy.data.objects['FrostCrystalSword_Blade']
canonical=rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@sword.matrix_world
sword.data.transform(canonical)
sword.parent=None;sword.matrix_world=Matrix.Identity(4)
sword.modifiers.clear()
for obj in list(bpy.context.scene.objects):
    if obj!=sword:bpy.data.objects.remove(obj,do_unlink=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
scene.world.color=(.35,.35,.35)
scene.view_settings.view_transform='AgX'
target=Vector((0,0,.015))
for name,location,energy,size in [('key',(1,-1.5,2),180,2),('fill',(-1,-.5,.5),100,1.3),('rim',(0,1,1),130,1)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('ReferenceCamera');cam=bpy.data.objects.new('ReferenceCamera',camera);scene.collection.objects.link(cam)
scene.camera=cam;camera.type='ORTHO';camera.ortho_scale=.57
P.mkdir(exist_ok=True)
for name,location in [('front',(0,-2,.015)),('side',(2,0,.015)),('angle',(.8,-1.6,.6))]:
    cam.location=location;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(P/('original_guard_'+name+'.png'));bpy.ops.render.render(write_still=True)
profile=[]
for z in range(-12,31,2):
    pts=[v.co for v in sword.data.vertices if z/100<=v.co.z<(z+2)/100]
    if pts:profile.append({'z_cm':[z,z+2],'x_cm':[min(v.x for v in pts)*100,max(v.x for v in pts)*100],'y_cm':[min(v.y for v in pts)*100,max(v.y for v in pts)*100],'vertices':len(pts)})
(P/'original_profile.json').write_text(json.dumps(profile,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'OriginalGuardReference.blend'))
