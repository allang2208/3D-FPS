"""Author the approved quarry hoist and ruined work shed, metres in Blender. No render."""
import bpy, math, json, random
from mathutils import Vector, Matrix
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HillsRiverLake20261117')
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
materials={name:bpy.data.materials.new(name) for name in ('Oak','Iron','Stone','Rope')}
parts=[];records=[];rng=random.Random(351117)
def box(name,at,size,mat='Oak',angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at)
    o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Worn edge','BEVEL');mod.width=.012 if mat!='Stone' else .025;mod.segments=2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    o.rotation_euler.z=angle;o.data.materials.append(materials[mat]);parts.append(o);return o
def beam(name,a,b,width,mat='Oak'):
    a,b=Vector(a),Vector(b);o=box(name,(a+b)/2,(width,width,(b-a).length),mat)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def cylinder(name,at,radius,depth,mat='Iron',rot=(0,0,0),vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=at,rotation=rot)
    o=bpy.context.object;o.name=name;o.data.materials.append(materials[mat]);parts.append(o);return o
def export(name):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    o=parts[0];o.name=name;o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    uv=o.data.uv_layers.active or o.data.uv_layers.new(name='SurfaceMetres')
    for f in o.data.polygons:
        axis=max(range(3),key=lambda i:abs(f.normal[i]))
        for idx in f.loop_indices:
            v=o.data.vertices[o.data.loops[idx].vertex_index].co
            uv.data[idx].uv=(v.y,v.z) if axis==0 else ((v.x,v.z) if axis==1 else (v.x,v.y))
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',
        axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    records.append(dict(name=name,slots=[m.name for m in o.data.materials],vertices=len(o.data.vertices)))
    o.location.x=len(records)*14;parts.clear()

# Two A-frames, braced boom, drum, cable and forged hook; stone feet have actual thickness.
for x in (-1.3,1.3):
    for y in (-1.3,1.3):
        box('stone foundation',(x,y,.20),(.85,.8,.4),'Stone',rng.uniform(-.1,.1))
        beam('A frame leg',(x,y,.35),(x,0,4.1),.25)
    beam('A frame tie',(x,-1.,1.2),(x,1.,1.2),.20)
beam('cross header',(-1.6,0,4.1),(1.6,0,4.1),.30)
beam('lifting boom',(0,-1.6,3.5),(0,2.8,5.),.30)
beam('boom brace',(0,-1.4,.5),(0,1.,4.4),.23)
for x in (-1.3,1.3):
    beam('long diagonal',(x,-1.2,.6),(-x,-.3,3.5),.15)
cylinder('timber drum',(0,-.9,1.5),.39,2.2,'Oak',(0,math.pi/2,0))
for x in (-1.15,1.15):cylinder('drum flange',(x,-.9,1.5),.48,.12,'Iron',(0,math.pi/2,0))
for x in [i*.08-.9 for i in range(24)]:
    bpy.ops.mesh.primitive_torus_add(major_radius=.395,minor_radius=.018,major_segments=24,minor_segments=6,
        location=(x,-.9,1.5),rotation=(0,math.pi/2,0))
    o=bpy.context.object;o.data.materials.append(materials['Rope']);parts.append(o)
beam('cable to pulley',(0,-.9,1.9),(0,2.65,4.85),.035,'Rope')
beam('hanging rope',(0,2.65,4.85),(0,2.65,1.1),.035,'Rope')
cylinder('pulley',(0,2.65,4.85),.24,.13,'Iron',(0,math.pi/2,0))
for i in range(7):
    a=math.pi*.15+i*.4;b=a+.4
    beam('forged hook',(0,2.65+.16*math.sin(a),.94+.16*math.cos(a)),
        (0,2.65+.16*math.sin(b),.94+.16*math.cos(b)),.055,'Iron')
box('cut stone load',(0,2.65,.22),(1.2,.9,.44),'Stone')
export('SM_QuarryTimberHoist')

# Both the kit and the targeted shelter rebuild share the same source.
from runpy import run_path
shed = run_path(str(Path(__file__).with_name('author_quarry_shed.py')))['assemble']()
records.append(dict(name=shed.name,slots=[m.name for m in shed.data.materials],vertices=len(shed.data.vertices)))
shed.location.x=len(records)*14
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'QuarryKit.blend'))
(OUT/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('QUARRY_KIT_SAVED',len(records))
