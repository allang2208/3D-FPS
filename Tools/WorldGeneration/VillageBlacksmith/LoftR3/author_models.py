"""Production-only background Blender: load-bearing loft, usable stairs and connected masonry flue."""
import bpy,bmesh,math,json,random,sys
from pathlib import Path
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE))
from design import *
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3';AUTH=OUT/'Authored';AUTH.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
rng=random.Random(1711173)
M={key:bpy.data.materials.new(key) for key in ('Oak','Iron','Stone','Soot','Firebrick')}
parts=[];collisions=[];assets=[]
def vec(p):return Vector((p[0]/100,-p[1]/100,p[2]/100))
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def uv(o,material,longaxis=2):
    for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
    layer=o.data.uv_layers.new(name='SurfaceMetres');layer.active_render=True
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
    name='SM_SmithLoft_'+role+('_R4' if role=='ArcadeFrame' else '')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=parts[0];o.name=name
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
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

# Front arcade and half-open west-front bay carry the reused upstairs masonry.
for x,y in [(-365,-389),(0,-389),(365,-389),(-389,-15),(-389,300),(0,300)]:
    box('Stone post shoe',(x,y,10),(34,34,20),'Stone',.7,True)
    box('Standing oak pier',(x,y,176),(25,25,312),'Oak',.55,True)
    for z in (40,308):peg((x,y-13,z))
beam('Front principal beam',(-395,-389,334),(395,-389,334),30,28,collision=True)
beam('West open bay beam',(-389,-389,334),(-389,15,334),28,28,collision=True)
beam('Rear support tie',(-370,300,334),(370,300,334),24,28,collision=True)
for x in (-365,0,365):
    for sign in (-1,1):
        if abs(x+sign*85)>395:continue
        beam('Arcade knee brace',(x,-389,258),(x+sign*82,-389,330),12,15)
beam('West front housed brace',(-365,-389,258),(-389,-305,330),12,15)
beam('West rear housed brace',(-389,-15,258),(-389,-100,330),12,15)
finish('ArcadeFrame')

# Three floor rectangles and a narrow wall margin leave a genuine stair well.
x0,x1,y0,y1=OPENING
regions=[(-HALF,HALF,-HALF,y0),(x1,HALF,y0,y1),(-HALF,HALF,y1,HALF),(-HALF,x0,y0,y1)]
for left,right,front,back in regions:
    count=math.ceil((right-left)/18);pitch=(right-left)/count
    for j in range(count):
        cx=left+(j+.5)*pitch
        box('Loft tongue-and-groove board',(cx,(front+back)/2,LOFT_Z-3),(pitch-.18,back-front,6),'Oak',.13)
    collider(((left+right)/2,(front+back)/2,LOFT_Z-6),(right-left,back-front,12))
    for yy in (front+12,back-12):beam('Floor bearing header',(left,yy,LOFT_Z-14),(right,yy,LOFT_Z-14),12,16)
    for yy in range(math.ceil(front+65),math.floor(back-40),65):beam('Floor joist',(left,yy,LOFT_Z-14),(right,yy,LOFT_Z-14),9,16)
beam('Stair trimmer right',(x1,y0,LOFT_Z-14),(x1,y1,LOFT_Z-14),15,20)
beam('Stair well rear header',(x0,y1,LOFT_Z-14),(x1,y1,LOFT_Z-14),15,20)
finish('UpperFloor')

# A 20-riser, 110 cm clear timber return stair; each top is a real collision support face.
for flight in range(2):
    cx=STAIR['first_x'] if flight==0 else STAIR['second_x'];direction=1 if flight==0 else -1
    start=STAIR['start_y'] if flight==0 else STAIR['turn_y'];base=flight*180
    for j in range(10):
        yy=start+direction*(j+.5)*28;top=base+(j+1)*18
        box('Solid stair tread',(cx,yy,top-3.5),(110,30,7),'Oak',.2)
        box('Stair riser',(cx,start+direction*j*28,top-9),(110,2.5,18),'Oak',.15)
        collider((cx,yy,top-9),(110,28,18))
        for xx in (cx-42,cx+42):peg((xx,yy,top-3),'X')
    for xx in (cx-50,cx+50):beam('Housed stair stringer',(xx,start,base+5),(xx,start+direction*280,base+169),10,20)
box('Turn landing',(-221,240,176),(238,120,8),'Oak',.25,True)
for xx in (-334,-108):
    for yy in (191,290):box('Landing leg',(xx,yy,86),(11,11,172),'Oak',.3,True)
finish('Stair')

def railing(a,b,height=103):
    beam('Continuous grasp rail',(a[0],a[1],a[2]+height),(b[0],b[1],b[2]+height),7,7,collision=True)
    beam('Lower guard rail',(a[0],a[1],a[2]+18),(b[0],b[1],b[2]+18),5,6)
    length=math.dist(a,b);n=max(1,math.ceil(length/70))
    for j in range(n+1):
        t=j/n;p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        box('Railing newel',(p[0],p[1],p[2]+height/2),(8,8,height+5),'Oak',.3,True)
    # Continuous slim collision follows the rail slope and prevents passing through the balusters.
    mid_a=(a[0],a[1],a[2]+height/2);mid_b=(b[0],b[1],b[2]+height/2)
    dx,dy=b[0]-a[0],b[1]-a[1];horizontal=math.hypot(dx,dy)
    segments=max(1,math.ceil(horizontal/30))
    for j in range(segments):
        t=(j+.5)/segments;p=tuple(mid_a[i]+(mid_b[i]-mid_a[i])*t for i in range(3))
        collider(p,(horizontal/segments+1,7,height),(0,math.degrees(math.atan2(dy,dx)),0))
    count=max(1,math.ceil(horizontal/13))
    for j in range(1,count):
        t=j/count;p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        box('Square oak baluster',(p[0],p[1],p[2]+height*.52),(3.6,3.6,height-23),'Oak',.15)
for cx in (STAIR['first_x']-58,STAIR['first_x']+58):railing((cx,-100,18),(cx,180,180))
for cx in (STAIR['second_x']-58,STAIR['second_x']+58):railing((cx,180,198),(cx,-100,360))
railing((-343,304,180),(-99,304,180))
railing((x1,OPENING[2],360),(x1,y1,360));railing((x0,y1,360),(x1,y1,360));railing((x0,y0,360),(-221,y0,360))
finish('Guardrails')

# A small real forge hearth, separate from the existing anvil/quench interaction asset.
box('Hearth foundation',(0,0,9),(154,112,18),'Stone',.8,True)
for xx in (-57,57):box('Firebox cheek',(xx,0,53),(24,100,70),'Stone',.6,True)
box('Firebox back',(0,43,53),(114,16,70),'Stone',.45,True)
box('Firebrick hearth bed',(0,0,79),(105,87,16),'Firebrick',.3,True)
for xx in range(-44,45,11):box('Forge grate',(xx,-5,89),(3,65,3),'Iron',.15)
box('Ash cleanout ledge',(0,-45,34),(89,14,8),'Firebrick',.25)
for xx in (-55,55):box('Hood support',(xx,40,130),(10,10,93),'Stone',.4,True)
# Four thick sloped hood plates, open underneath; outlet aligns with the rear duct.
outer=[(-70,-56,168),(70,-56,168),(70,48,168),(-70,48,168),(-27,16,246),(27,16,246),(27,58,246),(-27,58,246)]
for ids in [(0,1,5,4),(1,2,6,5),(3,0,4,7)]:
    o=mesh('Forged smoke canopy',[outer[i] for i in ids],[(0,1,2,3)],'Iron')
    mod=o.modifiers.new('Plate thickness','SOLIDIFY');mod.thickness=.004;apply(o,mod)
# Rear discharge opening, rather than an unbroken plate hidden inside the duct.
t=(201.-168.)/(246.-168.);wy=48+10*t;wx=70-43*t
for quad in [[(-70,48,168),(70,48,168),(wx,wy,201),(-wx,wy,201)],
             [(-wx,wy,201),(-25,wy,201),(-25,58,246),(-27,58,246)],
             [(25,wy,201),(wx,wy,201),(27,58,246),(25,58,246)]]:
    o=mesh('Hood discharge surround',quad,[(0,1,2,3)],'Iron');mod=o.modifiers.new('Plate thickness','SOLIDIFY');mod.thickness=.004;apply(o,mod)
box('Hood neck top',(0,37,246),(54,42,.4),'Iron',0)
for a,b in [((-70,-56,168),(70,-56,168)),((-70,-56,168),(-70,48,168)),((70,-56,168),(70,48,168))]:beam('Canopy rim',a,b,3,3,'Iron')
finish('ForgeHearth')

# Rear wall service infill. Fits the reused window opening without routing through solid masonry.
window_z=180.3198
hole_lo,hole_hi=201.,249.
left,right=-75.,75.;bottom,top=window_z-88,window_z+88
for c,s in [((0,0,(bottom+hole_lo)/2),(150,48,hole_lo-bottom)),((0,0,(hole_hi+top)/2),(150,48,top-hole_hi)),((-50,0,225),(50,48,48)),((50,0,225),(50,48,48))]:box('Mortared service infill',c,s,'Stone',.35,True)
finish('FlueInfill')

# Horizontal duct from hood to chimney, open at both ends. Origin is the hearth footprint centre.
for xx in (-25,25):box('Duct side',(xx,90,223.6),(1,144,45.2),'Iron',.08)
for zz in (201,246.2):box('Duct top bottom',(0,90,zz),(50,144,1),'Iron',.08)
for yy in (20,89,156):
    for xx in (-27,27):box('Collar side',(xx,yy,225),(4,4,54),'Iron',.12)
    for zz in (198,252):box('Collar crosspiece',(0,yy,zz),(58,4,4),'Iron',.12)
finish('SmokeDuct')

# A hollow stone chimney outside the existing roof; ashlar rings leave a real flue and side intake.
ring('Broad chimney foot',(0,0,10),(136,130),(42,42),20,'Stone',True)
for course in range(36):
    z=20+course*30+15
    outer=106 if course<4 else 92
    inner=44;thick=(outer-inner)/2
    for side in (-1,1):
        box('Shaft side ashlar',(side*(outer+inner)/4,0,z),(thick-.25,outer-.35,29.7),'Stone',.45)
    # 200..260 cm front courses leave the matching 48 cm duct port.
    for sign in (-1,1):
        yy=sign*(outer+inner)/4
        if sign==-1 and course in (6,7):continue
        if course%2:
            for xx in (-inner/4,inner/4):box('Staggered chimney ashlar',(xx,yy,z),(inner/2-.2,thick-.25,29.7),'Stone',.4)
        else:box('Chimney face ashlar',(0,yy,z),(inner,thick-.25,29.7),'Stone',.4)
for xx in (-34,34):collider((xx,0,560),(24,92,1080))
collider((0,34,560),(44,24,1080));collider((0,-34,110),(44,24,180));collider((0,-34,680),(44,24,840))
for xx in (-37.5,37.5):collider((xx,0,80),(31,106,120))
for yy in (-37.5,37.5):collider((0,yy,80),(44,31,120))
ring('Chimney crown',(0,0,1110),(120,120),(44,44),20,'Stone',True)
ring('Open chimney pot',(0,0,1135),(64,64),(44,44),30,'Firebrick',True)
for z in (275,590,870):
    for xx in (-49,49):beam('Wall tie',(xx,-44,z),(xx,-92,z),5,5,'Iron')
finish('Chimney')

# Ground-level dressings and chimney foundation blend the enlarged footprint into the existing yard.
for xx in (-270,-90,90,270):box('Front apron slab',(xx,-427,3),(179.4,72,6),'Stone',.5,True)
box('Chimney foundation pad',(200,480,2),(152,148,4),'Stone',.6,True)
finish('Apron')
(OUT/'design.json').write_text(json.dumps(DESCRIPTION,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'model-manifest.json').write_text(json.dumps({'assets':assets,'units':'centimetres in layout, metre FBX','authored_only':True,'gameplay_started':False},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageBlacksmith_LoftR3.blend'))
print('SMITH_LOFT_R3_AUTHORED',[(a['role'],a['lods'][0]['triangles']) for a in assets])
