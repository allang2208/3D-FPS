"""Production-only background Blender: load-bearing loft, usable stairs and connected masonry flue."""
import bpy,bmesh,math,json,random,sys
from pathlib import Path
from mathutils import Vector,Matrix,noise
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE.parent/'LoftR3'))
from design import *
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ChimneyR7';AUTH=OUT/'Authored';AUTH.mkdir(parents=True,exist_ok=True)
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
    name='SM_SmithLoft_'+role+'_R7'
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
    # Broad, irregular bearing stones; softly worn arrises and low-frequency chipped faces.
    o=box('Weathered bonded fieldstone',c,size,'HouseStone',min(size)*rng.uniform(.10,.16))
    mod=o.modifiers.new('Broad rock face subdivisions','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=1;apply(o,mod)
    seed=Vector((rng.uniform(0,30),rng.uniform(0,30),rng.uniform(0,30)))
    for v in o.data.vertices:
        # Stable spatial variation. Keep actual bed thickness; deform mainly the exposed faces.
        p=v.co.copy();n=v.normal
        broad=noise.noise_vector(p*4.2+seed)
        fine=noise.noise(p*17+seed)
        v.co += Vector((broad.x*.010,broad.y*.013,broad.z*.006))+n*(fine*.004)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    for f in o.data.polygons:f.use_smooth=True
    colors=o.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    moss=rng.uniform(0,.045);warm=rng.uniform(.015,.15)
    for f in o.data.polygons:
        for loop in f.loop_indices:colors.data[loop].color=(moss,warm,0.,1.)
    uv(o,'HouseStone')
    if c[2]>1070:
        o.data.materials.append(M['Soot']);o.data.update()
        for f in o.data.polygons:
            q=o.matrix_world@f.center
            if (abs(q.x)<.36 and abs(q.y)<.36) or q.z>11.435:f.material_index=1
    return o


def masonry_row(z0,z1,outer,index,port=False):
    inner=54.;depth=(outer-inner)/2;core=outer-13
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
            n=max(1,round((hi-lo)/rng.uniform(36,56)))
            weights=[rng.uniform(.68,1.32) for _ in range(n)]
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
while edges[-1]<1100:edges.append(min(1100,edges[-1]+rng.choice((23,27,31,35,38))))
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


(OUT/'model-manifest.json').write_text(json.dumps({'assets':assets,'native_material':'MI_Main_StoneWall_00A','purpose':'rounded irregular full bearing stones; recessed mortar and weathered rim'},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageBlacksmith_ChimneyR7.blend'))
print('SMITH_CHIMNEY_R7_AUTHORED',[(a['role'],a['lods'][0]['triangles']) for a in assets])
