"""Production-only background Blender: load-bearing loft, usable stairs and connected masonry flue."""
import bpy,bmesh,math,json,random,sys
from pathlib import Path
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE.parent/'LoftR3'))
from design import *
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6';AUTH=OUT/'Authored';AUTH.mkdir(parents=True,exist_ok=True)
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
    name='SM_SmithLoft_'+role+'_R6'
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

def stone(c,size):
    # Full bearing blocks, not scattered isolated protrusions. Bed faces remain level.
    o=box('Hand dressed bonded fieldstone',c,size,'HouseStone',rng.uniform(1.6,2.8))
    bm=bmesh.new();bm.from_mesh(o.data)
    for v in bm.verts:
        v.co.x+=rng.uniform(-.004,.004)
        v.co.y+=rng.uniform(-.006,.006)
        if abs(v.co.z)<size[2]/200-.025:v.co.z+=rng.uniform(-.004,.004)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    # Native Normandy stone uses vertex blend weights. Never import default white RGBA.
    colors=o.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    moss=rng.uniform(0,.025);warm=rng.uniform(.02,.22)
    for f in o.data.polygons:
        for loop in f.loop_indices:colors.data[loop].color=(moss,warm,0.,1.)
    uv(o,'HouseStone')
    return o

def masonry_row(z0,z1,outer,index,port=False):
    inner=54.;depth=(outer-inner)/2;core=outer-9
    # Back and side mortar occupy only the recessed joint core.
    for x in (-1,1):box('Recessed lime joint',(x*(core+inner)/4,0,(z0+z1)/2),((core-inner)/2,core,z1-z0),'HouseMortar',0)
    for y in (-1,1):
        if y==-1 and port and z0<258 and z1>196:continue
        box('Recessed lime joint',(0,y*(core+inner)/4,(z0+z1)/2),(inner,(core-inner)/2,z1-z0),'HouseMortar',0)
    # Alternating through-stones tie corners; narrow mortar beds are 1.2 cm.
    for side in range(4):
        long=(side<2)==(index%2==0)
        extent=outer if long else inner
        segments=[(-extent/2,extent/2,z0,z1)]
        if side==0 and port and z0<258 and z1>196:
            segments=[(-extent/2,-28,z0,z1),(28,extent/2,z0,z1)]
            if z0<196:segments.append((-28,28,z0,196))
            if z1>258:segments.append((-28,28,258,z1))
        for lo,hi,bottom,top in segments:
            if hi-lo<4 or top-bottom<4:continue
            n=max(1,round((hi-lo)/rng.uniform(46,58)))
            weights=[rng.uniform(.9,1.1) for _ in range(n)]
            cursor=lo
            for weight in weights:
                width=(hi-lo)*weight/sum(weights);mid=cursor+width/2;cursor+=width
                thick=depth-1.2;face=(outer+inner)/4
                if side<2:
                    c=(mid,(-1 if side==0 else 1)*face,(bottom+top)/2)
                    s=(width-1.2,thick,top-bottom-1.2)
                else:
                    c=((-1 if side==2 else 1)*face,mid,(bottom+top)/2)
                    s=(thick,width-1.2,top-bottom-1.2)
                stone(c,s)

masonry_row(0,24,182,0)
edges=[24,58,94,132]
while edges[-1]<1100:edges.append(min(1100,edges[-1]+rng.choice((30,32,34,36))))
for i,(a,b) in enumerate(zip(edges,edges[1:])):masonry_row(a,b,162 if a<132 else 146,i+1,True)
masonry_row(1100,1124,176,0);masonry_row(1124,1150,108,1)
# Five continuous collision faces retain a hollow flue and the service port.
for x in (-1,1):collider((x*50,0,562),(46,146,1076))
collider((0,50,562),(54,46,1076))
collider((0,-50,98),(54,46,196));collider((0,-50,679),(54,46,842))
for x in (-1,1):collider((x*59,0,66),(64,182,132))
for y in (-1,1):collider((0,y*59,66),(54,64,132))
for z in (285,590,870):
    for x in (-56,56):box('Forged masonry anchor',(x,-90,z),(5,52,5),'Iron',.3)
finish('Chimney')

# Reuse the complete accepted stair guard, then close the two exposed landing ends.
source=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3/Authored/VillageBlacksmith_LoftR3.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=['SM_SmithLoft_Guardrails']
o=dst.objects[0];bpy.context.collection.objects.link(o);o.matrix_world=Matrix.Identity(4)
o.data.materials.clear();o.data.materials.append(M['Oak'])
for f in o.data.polygons:f.material_index=0
for layer in list(o.data.uv_layers)[1:]:o.data.uv_layers.remove(layer)
o.data.uv_layers[0].name='UV0';parts.append(o)
manifest=json.loads((source.parents[1]/'model-manifest.json').read_text())
collisions.extend(next(a for a in manifest['assets'] if a['role']=='Guardrails')['collision_boxes'])
def guard(a,b):
    height=103
    beam('Landing continuous handrail',(a[0],a[1],a[2]+height),(b[0],b[1],b[2]+height),7,7,collision=True)
    beam('Landing bottom rail',(a[0],a[1],a[2]+18),(b[0],b[1],b[2]+18),5,6)
    length=math.dist(a,b);count=max(1,math.ceil(length/13))
    for j in range(count+1):
        t=j/count;p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        wide=7 if j in (0,count) else 3.6
        box('Landing oak upright',(p[0],p[1],p[2]+52),(wide,wide,103),'Oak',.2)
    collider(((a[0]+b[0])/2,(a[1]+b[1])/2,a[2]+51.5),(7,abs(b[1]-a[1])+7,103))
guard((-343,180,180),(-343,304,180));guard((-99,180,180),(-99,304,180))
# The wall-side upper well edge was entirely unguarded in R3.
guard((-352,-101,360),(-352,312,360))
finish('Guardrails')

# Anchored shutters: hinge pins are geometry and sit in the stone jamb; no second cross-frame.
for side in (-1,1):
    xhinge=side*50
    # Shutters fold nearly flat against the outside masonry, leaving the opening fully clear.
    angle=math.radians(side*8)
    for j in range(4):
        width=11.7;dx=side*((j+.5)*12)
        x=xhinge+dx*math.cos(angle);y=-42-abs(dx)*math.sin(abs(angle))
        p=box('Weathered shutter vertical plank',(x,y,30.2665),(11.65,3.7,111.5),'Oak',.28)
        p.rotation_euler.z=-angle
    for z in (-7,67):
        beam('Shutter forged strap',(xhinge,-44,z),(xhinge+side*44,-50.2,z),3.8,1.,'Iron')
        box('Hinge plate seated into masonry',(xhinge,-32,z),(5,24,10),'Iron',.2)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.009,depth=.14,location=vec((xhinge,-44,z)))
        q=bpy.context.object;q.name='Shutter hinge pin';q.data.materials.append(M['Iron']);uv(q,'Iron');parts.append(q)
finish('WindowShutters')

# Sign board is 150 x 66 cm. Mounts attach to the existing arcade beam at z=334 cm.
for j in range(3):
    z=-33+(j+.5)*22
    o=box('Painted aged oak sign board',(0,0,z),(150,4.6,21.75),'Sign',.45)
    o.data.materials.append(M['Oak'])
    for f in o.data.polygons:
        if f.normal.y<.7:f.material_index=1
    layer=o.data.uv_layers.new(name='UV1')
    bpy.context.view_layer.update()
    for f in o.data.polygons:
        for k in f.loop_indices:
            p=o.matrix_world@o.data.vertices[o.data.loops[k].vertex_index].co
            layer.data[k].uv=(.5-p.x/1.5,p.z/.66+.5)
for x in (-55,55):
    box('Rear sign cleat',(x,3.4,0),(5,2.2,62),'Oak',.25)
    box('Hand-forged hanger',(x,2.1,35),(3,.7,23),'Iron',.2)
    beam('Sign bracket to arcade',(x,2,43),(x,31,43),1.8,1.8,'Iron')
    box('Flush bracket mounting plate',(x,31,43),(6,1,17),'Iron',.2)
    for z in (37,49):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=.008,location=vec((x,30.2,z)))
        q=bpy.context.object;q.data.materials.append(M['Iron']);uv(q,'Iron');parts.append(q)
finish('BlacksmithSign')

# Ruin-only dressing remains within the same workshop footprint and clear of the stair route.
for i in range(9):
    x=rng.uniform(95,310);y=rng.uniform(-260,-100);length=rng.uniform(60,145)
    o=box('Split fallen beam',(x,y,4+i*.5),(length,8+rng.random()*8,5),'Oak',.3)
    o.rotation_euler.z=rng.uniform(-.7,.7)
for i in range(22):
    x=rng.uniform(170,340);y=rng.uniform(130,320)
    stone((x,y,4+rng.random()*5),(rng.uniform(12,28),rng.uniform(10,23),rng.uniform(6,13)))
for x,y in ((315,120),(310,240),(210,290)):
    o=box('Collapsed roof batten',(x,y,LOFT_Z+3),(115,8,5),'Oak',.5);o.rotation_euler.z=rng.uniform(-1.5,1.5)
finish('RuinDebris')

(OUT/'model-manifest.json').write_text(json.dumps({'assets':assets,'units':'centimetre layout / metre FBX','vertex_color_import':'REPLACE','gameplay_started':False,'rendered':False},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageBlacksmith_DetailR6.blend'))
print('SMITH_DETAIL_R6_AUTHORED',[(a['role'],a['lods'][0]['triangles']) for a in assets])
