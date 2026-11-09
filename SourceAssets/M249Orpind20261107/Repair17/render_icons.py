"""Produce catalog source renders from the two actual exported shells."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
r=Path(__file__).resolve().parent;out=r/'IconSources';out.mkdir(exist_ok=True)
cfg=json.loads((r/'model_recipe.json').read_text());flip=np.diag([100,-100,100,1]);back=np.diag([.01,-.01,.01,1])
to_display=back@np.linalg.inv(np.array(cfg['donor_mag_to_root']))@np.array(cfg['idle_mag_frame'])@flip
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
for capacity in (30,45):
    bpy.ops.wm.open_mainfile(filepath=str(r/'Exports'/('SM_m249_side_mag_'+str(capacity)+'.blend')),use_scripts=False)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.matrix_world=Matrix(to_display.tolist())
    ob.hide_render=False;ob.hide_set(False)
    apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
    scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    material=bpy.data.materials.new('M249 neutral ribbed polymer');material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.19,.19,.19,1);bsdf.inputs['Roughness'].default_value=.55
    ob.data.materials.clear();ob.data.materials.append(material)
    scene.world=bpy.data.worlds.new('M249 magazine catalog');scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.35,.35,.35,1);bg.inputs[1].default_value=.65
    points=[ob.matrix_world@v.co for v in ob.data.vertices];center=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))*.5
    data=bpy.data.cameras.new('Magazine profile');cam=bpy.data.objects.new('Magazine profile',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
    direction=Vector((1,.06,0)).normalized();cam.location=center+direction;cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    inv=cam.rotation_euler.to_matrix().transposed();q=[inv@(p-center) for p in points];data.ortho_scale=max(max(p.x for p in q)-min(p.x for p in q),max(p.y for p in q)-min(p.y for p in q))*1.18
    for name,offset,power,size in [('Key',(.8,-.5,1),90,.8),('Fill',(.6,.4,.3),55,.7),('Rim',(-.2,.8,.8),100,.6)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=center+Vector(offset);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/('Magazine_'+str(capacity)+'.blend')))
    scene.render.filepath=str(out/('Magazine_'+str(capacity)+'.png'));bpy.ops.render.render(write_still=True)
print('M249_MAGAZINE_ICON_SOURCES_SAVED',flush=True)
