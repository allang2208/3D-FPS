"""Render only the three actual shared menu icons from the saved model master."""
import bpy, json, math, runpy
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Components_Editable.blend'))
scene=bpy.context.scene
receipt=json.loads((P/'components.json').read_text(encoding='utf-8'))
runes=json.loads((P/'runes.json').read_text(encoding='utf-8'))['runes']
with bpy.data.libraries.load(str(P/'Kukri_Rune_Icons_Editable.blend'),link=False) as (src,dst):
    dst.objects=[r['object'] for r in runes]
for obj in dst.objects:scene.collection.objects.link(obj)
receipt['variants']+=runes
variants=[bpy.data.objects[v['object']] for v in receipt['variants']]
gray=runpy.run_path(str(P/'icon_grayscale.py'))
gray['apply_grayscale'](variants)
# Actual menu assets, not acceptance previews. Frame geometry stays in this scene only.
for obj in list(scene.objects):
    if obj not in variants:bpy.data.objects.remove(obj,do_unlink=True)
def simplemat(name,gray,metallic,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.node_tree.nodes.clear();b=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(b.outputs[0],output.inputs['Surface']);b.inputs['Base Color'].default_value=(gray,gray,gray,1)
    b.inputs['Metallic'].default_value=metallic;b.inputs['Roughness'].default_value=rough
    return m
frame=simplemat('Icon_Frame_Steel',.20,.9,.32)
back=simplemat('Icon_Recess',.035,.55,.58)
silver=simplemat('Icon_Rim',.38,.9,.24)
def cube(name,loc,scale,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object;o.name=name;o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('RoundedEdges','BEVEL');b.width=bevel;b.segments=4
        o.modifiers.new('FaceNormals','WEIGHTED_NORMAL')
    return o
cube('Frame_Back',(0,.08,0),(1.88,.10,1.88),back,.06)
for x,z,sx,sz in [(-.94,0,.17,2),( .94,0,.17,2),(0,-.94,2,.17),(0,.94,2,.17)]:
    cube('Frame_Rail',(x,0,z),(sx,.18,sz),frame,.035)
bpy.ops.mesh.primitive_torus_add(major_radius=.80,minor_radius=.018,major_segments=128,minor_segments=12,
                               location=(0,-.025,0),rotation=(math.pi/2,0,0))
bpy.context.object.name='Frame_InnerRing';bpy.context.object.data.materials.append(silver)
for x in (-.94,.94):
    for z in (-.94,.94):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.042,location=(x,-.107,z))
        bpy.context.object.scale=(1,.4,1);bpy.context.object.data.materials.append(silver)
cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(cam)
cam.location=(0,-4,0);cam.rotation_euler=(Vector()-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=2.12;scene.camera=cam
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.5
for name,loc,energy,size in [('Key',(-2,-3,3),280,4),('Fill',(2,-2,-1),150,3),('Rim',(1,-1,3),170,2)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.location=loc;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    lamp.data.energy=energy;lamp.data.size=size
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True;scene.cycles.samples=48
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
gray['neutral_output'](scene)
rotation=Matrix.Rotation(-math.pi/2,4,'Y')
for obj,entry in zip(variants,receipt['variants']):
    orientation=Matrix.Identity(4) if entry['slot']=='blade_2' else rotation
    points=[orientation@Vector(v) for v in obj.bound_box]
    center=sum(points,Vector())/8
    scale=1.42/max(max(v.x for v in points)-min(v.x for v in points),max(v.z for v in points)-min(v.z for v in points))
    obj.matrix_world=Matrix.Translation(Vector((0,-.12,0))-center*scale)@Matrix.Diagonal((scale,scale,scale,1))@orientation
for obj,entry in zip(variants,receipt['variants']):
    for other in variants:other.hide_render=other!=obj;other.hide_set(other!=obj)
    scene.render.filepath=entry['icon'];bpy.ops.render.render(write_still=True)
    print('COMPONENT_ICON_AUTHORED '+entry['id'],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Component_Icons_Editable.blend'))
print('KUKRI_ICONS_PRODUCTION_COMPLETE',flush=True)
