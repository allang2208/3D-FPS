"""Produce one real-model input per shared framed icon (20 masters, 26 bindings)."""
import bpy,json,math,runpy
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Refinement_Editable.blend'))
scene=bpy.context.scene
surfaces=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
manifest=json.loads((P.parent/'KukriFinalIntegration20261026/manifest.json').read_text(encoding='utf-8'))
variants={e['icon_key']:e for e in surfaces['variants']}
runes={e['icon_key']:e for e in json.loads((P.parent/'KukriComponentVariants20261026/runes.json').read_text(encoding='utf-8'))['runes']}
objects={}
def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0];scene.collection.objects.link(obj);return obj
for master in manifest['masters']:
    key=master['id']
    if key in variants:
        e=variants[key];obj=bpy.data.objects[e['object']];master['runtime_mesh']=e['mesh']
    elif key in runes:
        obj=append(P.parent/'KukriComponentVariants20261026/Kukri_Rune_Icons_Editable.blend',runes[key]['object'])
    elif key=='remove':
        bpy.ops.mesh.primitive_torus_add(major_radius=.50,minor_radius=.045,major_segments=96,minor_segments=12,rotation=(math.pi/2,0,0))
        obj=bpy.context.object
        bpy.ops.mesh.primitive_cube_add(size=1)
        bar=bpy.context.object;bar.dimensions=(.57,.075,.075);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bar.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join();obj.name='Icon_Remove'
        material=bpy.data.materials.new('Remove_Silver');material.use_nodes=True
        bs=material.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.35,.35,1);bs.inputs['Metallic'].default_value=.9;bs.inputs['Roughness'].default_value=.26
        obj.data.materials.clear();obj.data.materials.append(material)
    else:
        obj=append(P.parent/'KukriModules20261026/Kukri_Modules_Editable.blend',master['runtime_mesh'].rsplit('.',1)[-1])
    objects[key]=obj
    master.update(object=obj.name,input=str(P/'IconInputs'/(key+'.png')),source=str(P/'IconInputs'/(key+'.png')),
        output=str(P/'Icons'/(key+'.png')),surface_revision='KukriRefinement20261027',generate=True)
for obj in list(scene.objects):
    if obj not in objects.values():bpy.data.objects.remove(obj,do_unlink=True)
gray=runpy.run_path(str(P.parent/'KukriBladeVariants20261026/icon_grayscale.py'))
gray['apply_grayscale'](list(objects.values()))
camera=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(camera)
camera.location=(0,-4,0);camera.rotation_euler=(Vector()-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=1.90;scene.camera=camera
if not scene.world:scene.world=bpy.data.worlds.new('NeutralIconWorld')
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.28
for name,loc,energy,size in [('Key',(-1,-3,2),180,2),('Fill',(2,-2,-1),70,2),('Rim',(1,-1,3),90,2)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp);lamp.location=loc;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler();lamp.data.energy=energy;lamp.data.size=size
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';gray['neutral_output'](scene)
for m in manifest['masters']:
    obj=objects[m['id']]
    orientation=Matrix.Identity(4) if m['slot'] in ('blade_2','lanyard') or m['id']=='remove' else Matrix.Rotation(-math.pi/2,4,'Y')
    pts=[orientation@Vector(p) for p in obj.bound_box];center=sum(pts,Vector())/8
    span=max(max(p.x for p in pts)-min(p.x for p in pts),max(p.z for p in pts)-min(p.z for p in pts))
    scale=1.5/span
    obj.matrix_world=Matrix.Translation(-center*scale)@Matrix.Diagonal((scale,scale,scale,1))@orientation
    m['view']='hanging vertical' if m['slot']=='lanyard' else 'horizontal side profile' if m['slot']!='blade_2' else 'front symbol'
for m in sorted(manifest['masters'],key=lambda m:m['id']!='lanyard_knife_lanyard_tag'):
    obj=objects[m['id']]
    for other in objects.values():other.hide_set(other!=obj);other.hide_render=other!=obj
    scene.render.filepath=m['input'];bpy.ops.render.render(write_still=True)
    print('KUKRI_ICON_INPUT '+m['id'],flush=True)
manifest['rendering']='Image generation from the current physical model and approved standard frame'
(P/'icon-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_IconInputs_Editable.blend'))
