"""Production rune icon using the existing metal plate/rivet icon construction."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'Export';O.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
def material(name,color,metal=.8,emission=0.):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=.3
    n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emission
    return m
silver=material('Brushed silver frame',(.38,.4,.44));dark=material('Recessed graphite',(.025,.03,.04),.7)
blue=material('Swift blue rune',(.48,.5,.54),.65,.35);core=material('Bright cyan core',(.8,.82,.86),.5,.45)
def box(name,center,scale,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    m=o.modifiers.new('Machined bevel','BEVEL');m.width=bevel;m.segments=3;o.modifiers.new('Face normals','WEIGHTED_NORMAL');return o
box('Graphite plate',(0,.25,0),(1.72,.08,1.72),dark,.06)
for x in (-.83,.83):box('Vertical rim',(x,.14,0),(.16,.16,1.8),silver,.035)
for z in (-.83,.83):box('Horizontal rim',(0,.14,z),(1.8,.16,.16),silver,.035)
bpy.ops.mesh.primitive_torus_add(major_radius=.69,minor_radius=.027,major_segments=96,minor_segments=12,location=(0,.13,0),rotation=(math.pi/2,0,0));bpy.context.object.data.materials.append(silver)
for x in (-.81,.81):
    for z in (-.81,.81):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=.037,location=(x,.025,z));bpy.context.object.scale=(1,.45,1);bpy.context.object.data.materials.append(silver)
def stroke(name,points,radius,mat):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=radius;c.bevel_resolution=3
    s=c.splines.new('POLY');s.points.add(len(points)-1)
    for p,(x,z) in zip(s.points,points):p.co=(x,-.03,z,1)
    o=bpy.data.objects.new(name,c);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
# A split diamond, four crushing wedges and broken rings identify destruction.
stroke('Split diamond left',[(-.04,.48),(-.36,0),(-.04,-.48)],.035,blue)
stroke('Split diamond right',[(.04,.48),(.36,0),(.04,-.48)],.035,blue)
for sign in (-1,1):
    stroke('Crushing side wedge',[(sign*.52,.24),(sign*.31,0),(sign*.52,-.24)],.028,blue)
    stroke('Crushing end wedge',[(-.17,sign*.52),(0,sign*.31),(.17,sign*.52)],.025,blue)
    stroke('Core fracture',[(sign*.02,sign*.27),(sign*.09,sign*.09),(-sign*.05,-sign*.1)],.014,core)
for angle in (30,120,210,300):
    points=[(.59*math.cos(math.radians(angle+i)),.59*math.sin(math.radians(angle+i))) for i in range(48)]
    stroke('Broken containment ring',points,.012,blue)
box('Crystalline core',(0,-.035,0),(.105,.05,.105),core,.01).rotation_euler.y=math.pi/4
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
world=bpy.data.worlds.new('Rune icon world');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.15,.15,.15,1)
bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.86;scene.camera=cam
for loc,power,size in [((-2,-3,3),350,3),((2,-2,1),220,2),((0,-1,-2),100,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'ue_runebound_warhammer_blade_2_destruction_mana_rune.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'DestructionManaRune_Icon_Editable.blend'))
bpy.ops.render.render(write_still=True)
(P/'icon_receipt.json').write_text(json.dumps({'complete':True,'icon':scene.render.filepath,'purpose':'production UI icon','acceptance_rendered':False,'tested':False},indent=2),encoding='utf-8')
print('DESTRUCTION_MANA_RUNE_ICON_AUTHORED')
