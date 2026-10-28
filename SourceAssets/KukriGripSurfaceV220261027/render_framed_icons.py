"""Render only the three actual shared menu icons from the saved model master."""
import bpy, json, math, runpy
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Grip_SurfaceV2_Editable.blend'))
scene=bpy.context.scene
receipt=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
variants=[bpy.data.objects[v['object']] for v in receipt['variants']]
gray=runpy.run_path(str(P.parent/'KukriBladeVariants20261026/icon_grayscale.py'))
gray['apply_grayscale'](variants)
# Actual menu assets, not acceptance previews. Frame geometry stays in this scene only.
for obj in list(scene.objects):
    if obj not in variants:bpy.data.objects.remove(obj,do_unlink=True)
def simplemat(name,gray,metallic,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.node_tree.nodes.clear();b=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(b.outputs[0],output.inputs['Surface']);b.inputs['Base Color'].default_value=(gray,gray,gray,1)
    b.inputs['Metallic'].default_value=metallic;b.inputs['Roughness'].default_value=rough
    noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220
    noise.inputs['Detail'].default_value=2
    bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00065
    bump.inputs['Strength'].default_value=.23
    m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    m.node_tree.links.new(bump.outputs[0],b.inputs['Normal'])
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
vertices=[];faces=[];segments=192
for radius,depth in ((.835,-.062),(.790,-.062),(.835,-.025),(.790,-.025)):
    vertices.extend((radius*math.cos(i*2*math.pi/segments),depth,radius*math.sin(i*2*math.pi/segments)) for i in range(segments))
for i in range(segments):
    j=(i+1)%segments
    for a,b in ((0,1),(2,0),(1,3),(3,2)):
        faces.append((a*segments+i,a*segments+j,b*segments+j,b*segments+i))
mesh=bpy.data.meshes.new('Frame_InnerRing');mesh.from_pydata(vertices,[],faces);mesh.update()
ring=bpy.data.objects.new('Frame_InnerRing',mesh);scene.collection.objects.link(ring)
ring.data.materials.append(silver)
bevel=ring.modifiers.new('MachinedRim','BEVEL');bevel.width=.005;bevel.segments=3
ring.modifiers.new('RimNormals','WEIGHTED_NORMAL')
for x in (-.91,.91):
    for z in (-.91,.91):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.136,depth=.045,location=(x,-.115,z),rotation=(math.pi/2,0,math.pi/8))
        plate=bpy.context.object;plate.name='Frame_CornerPlate';plate.data.materials.append(frame)
        bevel=plate.modifiers.new('PlateBevel','BEVEL');bevel.width=.012;bevel.segments=3
        plate.modifiers.new('PlateNormals','WEIGHTED_NORMAL')
        bpy.ops.mesh.primitive_torus_add(major_radius=.061,minor_radius=.006,major_segments=48,minor_segments=8,location=(x,-.145,z),rotation=(math.pi/2,0,0))
        bpy.context.object.data.materials.append(silver)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.053,location=(x,-.15,z))
        bpy.context.object.scale=(1,.38,1);bpy.context.object.data.materials.append(silver)
        for polygon in bpy.context.object.data.polygons:polygon.use_smooth=True
cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));scene.collection.objects.link(cam)
cam.location=(0,-4,0);cam.rotation_euler=(Vector()-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=2.12;scene.camera=cam
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.32
for name,loc,energy,size in [('Key',(-2,-3,3),175,3),('Fill',(2,-2,-1),50,2),('Rim',(1,-1,3),90,2)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.location=loc;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    lamp.data.energy=energy;lamp.data.size=size
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True;scene.cycles.samples=64;scene.cycles.use_denoising=True
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
    print('GRIP_SURFACE_V2_ICON_AUTHORED '+entry['id'],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Grip_SurfaceV2_FramedIcons_Editable.blend'))
print('KUKRI_ICONS_PRODUCTION_COMPLETE',flush=True)
