"""Production-only background Blender: load-bearing loft, usable stairs and connected masonry flue."""
import bpy,bmesh,math,json,random,sys
from pathlib import Path
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE.parent/'LoftR3'))
from design import *
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7';AUTH=OUT/'Authored';AUTH.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
rng=random.Random(1711173)
M={key:bpy.data.materials.new(key) for key in ('Oak','Iron','Stone','Soot','Firebrick','HouseStone','HouseMortar','Sign')}
parts=[];collisions=[];assets=[]
def vec(p):return Vector((p[0]/100,-p[1]/100,p[2]/100))
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def uv(o,material,longaxis=2):
    for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
    layer=o.data.uv_layers.new(name='UV0');layer.active_render=True
    offset=(rng.uniform(0,.7),rng.uniform(0,.7))
    for f in o.data.polygons:
        dominant=max(range(3),key=lambda i:abs(f.normal[i]));axes=[i for i in range(3) if i!=dominant]
        for index in f.loop_indices:
            p=o.data.vertices[o.data.loops[index].vertex_index].co
            if material=='Oak' and dominant!=longaxis:
                transverse=next(i for i in range(3) if i not in (dominant,longaxis))
                co=(p[transverse]+offset[0],p[longaxis]/2+offset[1])
            else:co=(p[axes[0]],p[axes[1]])
            layer.data[index].uv=co
def collider(c,s,rot=(0,0,0)):collisions.append({'center':list(c),'size':list(s),'rotation':list(rot)})
def box(name,c,s,material='Oak',bevel=.3,collision=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=vec(c));o=bpy.context.object;o.name=name;o.dimensions=Vector(s)/100
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(M[material]);parts.append(o)
    if bevel:
        m=o.modifiers.new('Worn arris','BEVEL');m.width=bevel/100;m.segments=3;m.limit_method='ANGLE';apply(o,m)
        for f in o.data.polygons:f.use_smooth=True
        m=o.modifiers.new('Broad face normals','WEIGHTED_NORMAL');m.keep_sharp=True;apply(o,m)
    uv(o,material,max(range(3),key=lambda i:s[i]))
    if collision:collider(c,s)
    return o
def beam(name,a,b,w=12,d=16,material='Oak',collision=False):
    direction=vec(b)-vec(a);o=box(name,(0,0,0),(direction.length*100,w,d),material,.3)
    o.rotation_mode='QUATERNION';o.rotation_quaternion=direction.to_track_quat('X','Z');o.location=(vec(a)+vec(b))/2
    if collision:
        dx,dy,dz=[b[i]-a[i] for i in range(3)];length=math.sqrt(dx*dx+dy*dy+dz*dz)
        collider([(a[i]+b[i])/2 for i in range(3)],(length,w,d),(math.degrees(math.atan2(dz,math.hypot(dx,dy))),math.degrees(math.atan2(dy,dx)),0))
    return o
def mesh(name,vertices,faces,material):
    data=bpy.data.meshes.new(name);data.from_pydata([vec(p) for p in vertices],[],faces);data.update()
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);parts.append(o);data.materials.append(M[material])
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free();uv(o,material);return o
def peg(c,axis='Y'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=.008,depth=.014,location=vec(c));o=bpy.context.object;o.name='Oak drawbore peg'
    if axis=='Y':o.rotation_euler.x=math.pi/2
    else:o.rotation_euler.y=math.pi/2
    o.data.materials.append(M['Oak']);parts.append(o);uv(o,'Oak')
def ring(name,c,outer,inner,height,mat='Stone',collision=False):
    x,y,z=c;ox,oy=outer;ix,iy=inner
    for xx in (-1,1):box(name,(x+xx*(ox+ix)/4,y,z),((ox-ix)/2,oy,height),mat,.4,collision)
    for yy in (-1,1):box(name,(x,y+yy*(oy+iy)/4,z),(ix,(oy-iy)/2,height),mat,.4,collision)
def finish(role):
    global parts,collisions
    name='SM_SmithLoft_'+role+'_R7b'
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=parts[0];o.name=name
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    for layer in o.data.uv_layers:layer.name='UV0' if layer==o.data.uv_layers[0] else 'UV1'
    o.data.uv_layers.active_index=0
    mod=o.modifiers.new('Game triangles','TRIANGULATE');mod.keep_custom_normals=True;apply(o,mod)
    lods=[]
    for level,ratio in [(0,1.),(1,.5),(2,.22)]:
        q=o
        if level:
            q=o.copy();q.data=o.data.copy();bpy.context.collection.objects.link(q);q.name=name+'_LOD'+str(level)
            mod=q.modifiers.new('Distance detail','DECIMATE');mod.ratio=ratio;mod.delimit={'MATERIAL','UV'};apply(q,mod)
        active(q);path=AUTH/(name+(f'_LOD{level}' if level else '')+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
        q.data.calc_loop_triangles();lods.append({'level':level,'file':str(path),'triangles':len(q.data.loop_triangles)})
        if level:bpy.data.objects.remove(q,do_unlink=True)
    assets.append({'role':role,'name':name,'lods':lods,'materials':[m.name for m in o.data.materials],'collision_boxes':collisions})
    o.location=(len(assets)*12,0,0);parts=[];collisions=[]

# Author directly in final centimetres: X outside, Y across opening, Z up.
# All leaf vertices are local to the actual hinge pins. No bounds-derived offset.
HALF=74.;HEIGHT=162.;WIDTH=HALF-.45

def cylinder(name,c,radius,height,mat='Iron',axis='Z',vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius/100,depth=height/100,location=vec(c))
    o=bpy.context.object;o.name=name
    if axis=='X':o.rotation_euler.y=math.pi/2
    elif axis=='Y':o.rotation_euler.x=math.pi/2
    o.data.materials.append(M[mat]);uv(o,mat);parts.append(o)
    m=o.modifiers.new('Forging edge','BEVEL');m.width=.0012;m.segments=2;apply(o,m)
    return o

def rivet(c):
    cylinder('Domed clinch nail',c,.48,.4,axis='X',vertices=10)

def pull(c):
    bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=8,location=vec(c),major_radius=.028,minor_radius=.004)
    o=bpy.context.object;o.name='Hand forged pull ring';o.rotation_euler.y=math.pi/2
    o.data.materials.append(M['Iron']);uv(o,'Iron');parts.append(o)

# Narrow rebated stops sit behind the closed boards and bury their rear edge in the stone.
for side in (-1,1):
    box('Recessed oak jamb stop',(-14,side*72.5,0),(17,5.5,166),'Oak',.25)
    collider((-14,side*72.5,0),(17,5.5,166))
box('Recessed oak head stop',(-14,0,80.5),(17,145,5),'Oak',.25)
collider((-14,0,80.5),(17,145,5))
# Four fixed pintles have 20 cm embedment tails and mounting plates at the stone face.
for side in (-1,1):
    for z in (-51.,51.):
        y=side*HALF
        box('Recessed masonry anchor',(-15,y,z),(31,3.2,4.2),'Iron',.17)
        box('Pintle mounting plate',(-7,y,z),(1.8,9,17),'Iron',.25)
        cylinder('Fixed pintle pin',(0,y,z),.85,17)
        for dz in (-5.8,5.8):rivet((-5.8,y,z+dz))
        collider((-10,y,z),(20,9,17))
# A single deep sill, not a cross frame. Interior latch ring remains reachable when open.
box('Weathered oak inner sill',(-52,0,-84.5),(104,153,6),'Oak',.5)
collider((-52,0,-84.5),(104,153,6))
box('Sill pull mounting foot',(-69,0,-77.8),(8,8,1.4),'Iron',.15)
box('Sill pull bracket',(-69,0,-73),(1.8,6,10),'Iron',.15)
pull((-70.3,0,-68.5));collider((-69,0,-71),(4,9,15))
finish('WindowMount')

for side,role in ((1,'WindowLeft'),(-1,'WindowRight')):
    # Four boards, restrained unevenness, real gaps, tongue-and-groove shadow lines.
    for j in range(4):
        span=WIDTH/4
        c=(-2.8,side*((j+.5)*span),rng.uniform(-.18,.18))
        o=box('Quarter sawn oak shutter board',c,(4.8,span-.16,HEIGHT-rng.uniform(0,.35)),'Oak',.22)
        # Tiny uneven arrises give hand-planed silhouettes, without crumpling broad faces.
        uv(o,'Oak',2)
    # Inner ledges and diagonal load brace sit on the room side; grain follows each beam.
    for z in (-51.,51.):
        beam('Rear oak cross ledge',(-6.1,side*3,z),(-6.1,side*(WIDTH-2),z),6.5,3.1)
    beam('Traditional diagonal shutter brace',(-6.5,side*6,-46),(-6.5,side*(WIDTH-7),46),6.,2.6)
    for z in (-51.,51.):
        # Tapered forged straps wrap around the stationary pintle; tips do not stick out.
        vertices=[(.2,side*1,z-2.5),(.2,side*(WIDTH-7),z-1.2),(.2,side*(WIDTH-3),z),(.2,side*(WIDTH-7),z+1.2),(.2,side*1,z+2.5)]
        vertices+= [(x-.65,y,zz) for x,y,zz in vertices]
        faces=[(0,1,2,3,4),(9,8,7,6,5)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)]
        o=mesh('Hammer tapered iron strap',vertices,faces,'Iron')
        m=o.modifiers.new('Soft forged edge','BEVEL');m.width=.001;m.segments=2;apply(o,m)
        for yy in (7,25,45,WIDTH-9):rivet((.5,side*yy,z))
        cylinder('Moving hinge knuckle',(0,0,z),1.2,8.5)
    box('Interior pull backplate',(-8.1,side*(WIDTH-9),-8),(1.,5.,10.),'Iron',.2)
    pull((-9.1,side*(WIDTH-9),-10))
    for zz in (-4,-12):rivet((-8.8,side*(WIDTH-9),zz))
    collider((-2.8,side*WIDTH/2,0),(4.8,WIDTH,HEIGHT))
    finish(role)

(OUT/'model-manifest.json').write_text(json.dumps({'assets':assets,'hinges_cm':[[0,-HALF,0],[0,HALF,0]],'opening_degrees':105,'units':'final centimetres; authored hinge origins'},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageBlacksmith_WindowR7.blend'))
print('SMITH_WINDOW_R7_AUTHORED',[(a['role'],a['lods'][0]['triangles']) for a in assets])
