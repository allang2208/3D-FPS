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

# Nine by six metre shed. Masonry courses have a real 1.6 m door and missing wall sections.
for side in (-1,1):
    for j in range(12):
        for row in range(5):
            if side==1 and j>7 and row>1:continue
            if side==-1 and 4<=j<=6 and row in (2,3):continue
            x=side*4.5;y=-2.75+j*.5
            box('side fieldstone',(x,y,.28+row*.48),(.5,.48,.46),'Stone',rng.uniform(-.035,.035))
for j in range(18):
    x=-4.25+j*.5
    for row in range(6 if j<10 else 3):
        box('rear fieldstone',(x,3.,.28+row*.48),(.48,.5,.46),'Stone',rng.uniform(-.03,.03))
    if abs(x)>.85:
        for row in range(4 if j<5 else 3):
            box('door wall',(x,-3.,.28+row*.48),(.48,.5,.46),'Stone',rng.uniform(-.03,.03))
beam('door lintel',(-1.05,-3.,2.25),(1.05,-3.,2.25),.22)
for y in (-2.7,0.,2.7):
    beam('left rafter',(-4.6,y,2.85),(0,y,4.1),.18)
    if y>0:beam('right broken rafter',(0,y,4.1),(3.4,y,3.16),.18)
beam('ridge',(0,-3.2,4.1),(0,3.3,4.1),.22)
for i in range(15):
    y=-3.+i*.42
    if i in (2,3,9,12):continue
    beam('surviving roof plank',(-4.7,y,2.90),(-.1,y,4.18),.23)
for i in range(14):
    x=rng.uniform(-3.8,3.8);y=rng.uniform(-2.,2.4)
    box('fallen timber',(x,y,.13),(rng.uniform(1.4,3.1),.17,.14),'Oak',rng.uniform(-2.,2.))
box('stone cutting bench',(-2.,1.5,.65),(2.1,.85,.35),'Stone')
for x in (-2.7,-1.3):box('bench support',(x,1.5,.28),(.32,.6,.55),'Stone')
export('SM_QuarryRuinedShed')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'QuarryKit.blend'))
(OUT/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('QUARRY_KIT_SAVED',len(records))
