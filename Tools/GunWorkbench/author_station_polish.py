"""Author the reference-led desktop kit in background Blender; never render/run UE."""
import bpy, bmesh, json, math, re
from pathlib import Path
from mathutils import Vector, Matrix

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/GunWorkbenchPolish20260928'
OUT=ROOT/'Authored'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=PROJECT/'SourceAssets/WorkbenchBuildable20260924/Authored/StandaloneWorkbench.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
base=bpy.data.objects['SM_WBStandalone_Workbench']
for obj in list(bpy.data.objects):
    if obj!=base:bpy.data.objects.remove(obj,do_unlink=True)
base.hide_set(False);base.name='Retained_Table'
def canon(s):return re.sub(r'[._][0-9]{3}$','',s)
wood={'WSBench_BenchWood','WSBench_EndGrain'}
frame={'WSDetail_RackPaint','WSSculpt_Machined','WSSculpt_RubberGrip'}
bm=bmesh.new();bm.from_mesh(base.data)
remove=[]
for f in bm.faces:
    name=canon(base.data.materials[f.material_index].name)
    if not(name in wood or (name in frame and max((base.matrix_world@v.co).z for v in f.verts)<.88)):remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(base.data);bm.free()
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
active(base);bpy.ops.object.material_slot_remove_unused()

SPEC={
 'GW3_Rubber':{'color':[.021,.025,.024],'roughness':.83,'metallic':0},
 'GW3_Index':{'color':[.19,.21,.20],'roughness':.75,'metallic':0},
 'GW3_Mat':{'color':[.026,.030,.028],'roughness':.78,'metallic':0},
 'GW3_SpunSteel':{'color':[.48,.51,.53],'roughness':.29,'metallic':1},
 'GW3_Label':{'color':[.70,.69,.62],'roughness':.72,'metallic':0},
 'GW3_Paint':{'color':[.043,.052,.049],'roughness':.42,'metallic':.55},
 'GW3_Steel':{'color':[.44,.48,.50],'roughness':.3,'metallic':1},
 'GW3_DarkSteel':{'color':[.11,.13,.14],'roughness':.36,'metallic':.9},
 'GW3_Brass':{'color':[.55,.36,.13],'roughness':.31,'metallic':1},
 'GW3_Nylon':{'color':[.69,.70,.65],'roughness':.53,'metallic':0},
 'GW3_Blue':{'color':[.035,.11,.17],'roughness':.36,'metallic':.65},
 'GW3_Amber':{'color':[.19,.065,.009],'roughness':.22,'metallic':0},
 'GW3_Diffuser':{'color':[.82,.78,.65],'roughness':.38,'metallic':0,'emissive':[1.3,1.15,.85]},
}
MATS={}
for name,s in SPEC.items():
    m=bpy.data.materials.new(name);m.diffuse_color=(*s['color'],1);m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF')
    if shader is None:
        shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for socket,key in [('Base Color','color'),('Roughness','roughness'),('Metallic','metallic')]:
        shader.inputs[socket].default_value=(*s[key],1) if key=='color' else s[key]
    if 'emissive' in s:shader.inputs['Emission Color'].default_value=(*s['emissive'],1)
    MATS[name]=m
parts=[base]
def finish(o,name,mat,bevel=0):
    o.name=name;o.data.materials.append(MATS[mat]);parts.append(o)
    if bevel:
        for face in o.data.polygons:face.use_smooth=True
        o.data.set_sharp_from_angle(angle=math.radians(55))
        active(o);mod=o.modifiers.new('Machined edge radius','BEVEL');mod.width=bevel;mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        normal=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');normal.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=normal.name)
    return o
def box(name,loc,dim,mat,bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat,bevel)
def lathe(name,profile,mat,loc=(0,0,0),axis=(0,0,1),segments=48,flutes=0):
    # Closed radial section with rings from base up, then back down the inner wall.
    verts=[];faces=[]
    for z,r in profile:
        for i in range(segments):
            a=2*math.pi*i/segments;rr=r*(1-.055*(.5+.5*math.cos(a*(flutes if flutes>1 else 12)))) if flutes else r
            verts.append((rr*math.cos(a),rr*math.sin(a),z))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces.append(tuple(reversed(range(segments))));faces.append(tuple((len(profile)-1)*segments+i for i in range(segments)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o)
    o.location=loc;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis).normalized())
    finish(o,name,mat)
    o['turned_surface']=True
    distances=[0.0]
    for pa,pb in zip(profile,profile[1:]):distances.append(distances[-1]+math.hypot(pb[0]-pa[0],pb[1]-pa[1]))
    uv=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        if face.index<(len(profile)-1)*segments:
            j,i=divmod(face.index,segments)
            v0=distances[j]/distances[-1];v1=distances[j+1]/distances[-1]
            for li,co in zip(face.loop_indices,[(i/segments,v0),((i+1)/segments,v0),((i+1)/segments,v1),(i/segments,v1)]):uv.data[li].uv=co
        else:
            r=max(v[1] for v in profile)
            for li in face.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(.5+co.x/(2*r),.5+co.y/(2*r))
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    mesh.set_sharp_from_angle(angle=math.radians(40))
    return o
def cylinder(name,a,b,r,mat,segments=32):
    v=Vector(b)-Vector(a);edge=min(.0005,v.length*.2);return lathe(name,[(0,r*.94),(edge,r),(v.length-edge,r),(v.length,r*.94)],mat,a,v,segments)
def tube(name,points,r,mat):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=r;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,v in zip(spline.points,points):p.co=(*v,1)
    o=bpy.data.objects.new(name,curve);bpy.context.scene.collection.objects.link(o);active(o);bpy.ops.object.convert(target='MESH')
    finish(bpy.context.object,name,mat)
def screw(name,pos,axis=(1,0,0),r=.008):
    p=Vector(pos);v=Vector(axis);cylinder(name,p,p+v*.004,r,'GW3_DarkSteel')
    cylinder(name+' hex socket',p+v*.004,p+v*.0044,r*.45,'GW3_Rubber',6)
def rounded_rect(w,h,r,z):
    v=[]
    for x,y,start in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for i in range(13):
            a=math.radians(start+i*90/12);v.append((x+r*math.cos(a),y+r*math.sin(a),z))
    return v
top=.939
# Thin flat mat stays below every accepted assembly parking position.
verts=rounded_rect(.54,1.3,.025,top+.001)+rounded_rect(.54,1.3,.025,top+.006)
n=len(verts)//2;faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
for i in range(n):faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
mesh=bpy.data.meshes.new('Silicone mat');mesh.from_pydata(verts,[],faces);mesh.update()
o=bpy.data.objects.new('Silicone mat',mesh);bpy.context.scene.collection.objects.link(o);o.location.x=.82;finish(o,o.name,'GW3_Mat',.0008)
border=[(x+.82,y,z) for x,y,z in rounded_rect(.51,1.27,.022,top+.0062)];tube('Inset mat seam',border+[border[0]],.00065,'GW3_Index')
for i in range(61):
    box('Graduation',(.82-.235,-.60+i*.02,top+.0065),(.013 if i%5==0 else .006,.00065,.00035),'GW3_Index',0)

# Two spun dishes: convex underside, shallow concave interior and rolled lip.
for idx,(x,y,r) in enumerate([(-.10,-.97,.092),(-.34,-.97,.072)]):
    lathe('Magnetic dish '+str(idx+1),[(0,.001),(0,r*.63),(.002,r*.78),(.007,r*.95),(.018,r),(.020,r*.99),(.021,r*.97),(.019,r*.95),(.008,r*.90),(.004,r*.74),(.004,.001)],'GW3_SpunSteel',(x,y,top+.002),segments=96)
    lathe('Dish rubber foot '+str(idx+1),[(0,.001),(0,r*.48),(.002,r*.48),(.002,.001)],'GW3_Rubber',(x,y,top),segments=48)
# Turned punches and driver lie across the side wing; fine ridges are modeled.
def grip_rings(name,origin,length,radius,axis=(1,0,0)):
    # Cut diamond knurl on a continuous sleeve, with plain end collars.
    segments,rows=64,32;verts=[];faces=[]
    for j in range(rows+1):
        t=j/rows;edge=min(1,t*12,(1-t)*12)
        for i in range(segments):
            a=i*2*math.pi/segments
            groove=(1-abs(math.sin(a*8+t*math.pi*16)*math.sin(a*8-t*math.pi*16)))
            r=radius-.00022*groove*edge
            verts.append((r*math.cos(a),r*math.sin(a),t*length))
    for j in range(rows):
        for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name+' diamond knurl',me);bpy.context.scene.collection.objects.link(o)
    o.location=origin;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis));finish(o,o.name,'GW3_DarkSteel')
    uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        j,i=divmod(f.index,segments)
        for li,co in zip(f.loop_indices,[(i/segments,j/rows),((i+1)/segments,j/rows),((i+1)/segments,(j+1)/rows),(i/segments,(j+1)/rows)]):uv.data[li].uv=co
        f.use_smooth=True
    o['turned_surface']=True
    for t in [0,length-.0015]:cylinder(name+' plain collar',Vector(origin)+Vector(axis)*t,Vector(origin)+Vector(axis)*(t+.0015),radius,'GW3_Steel')
for i in range(3):
    x,y,z=-.75,-.78-i*.058,top+.007
    lathe('Pin punch '+str(i+1),[(0,.0045),(.004,.006),(.07,.006),(.075,.004),(.106,.003),(.118,.0016+i*.0004),(.16,.0016+i*.0004)],'GW3_Steel',(x,y,z),(1,0,0),32)
    grip_rings('Punch', (x+.005,y,z),.062,.00625)
x,y,z=-.83,-1.005,top+.012
lathe('Precision driver handle',[(0,.004),(.003,.009),(.018,.012),(.082,.011),(.100,.006),(.103,.005)],'GW3_Rubber',(x,y,z),(1,0,0),60,1)
lathe('Driver rotating cap',[(0,.006),(.002,.010),(.011,.010),(.014,.008)],'GW3_Blue',(x-.01,y,z),(1,0,0),48)
cylinder('Driver shaft',(x+.1,y,z),(x+.2,y,z),.003,'GW3_Steel')
box('Ground slotted driver blade',(x+.209,y,z),(.018,.0045,.0012),'GW3_DarkSteel',.00025)
lathe('Driver ferrule',[(0,.005),(.002,.006),(.009,.006),(.012,.004)],'GW3_Steel',(x+.098,y,z),(1,0,0))

# Dual-face mallet with tapered, fluted grip and steel neck.
x,y,z=-.87,-1.155,top+.017
lathe('Mallet grip',[(0,.012),(.006,.014),(.08,.0115),(.13,.010),(.14,.007)],'GW3_Rubber',(x,y,z),(1,0,0),60,1)
cylinder('Mallet neck',(x+.13,y,z),(x+.218,y,z),.006,'GW3_DarkSteel')
lathe('Mallet head',[(0,.014),(.004,.016),(.044,.016),(.048,.014)],'GW3_DarkSteel',(x+.214,y-.024,z),(0,1,0))
for sign,mat in [(-1,'GW3_Brass'),(1,'GW3_Nylon')]:
    lathe('Replaceable mallet face',[(0,.0145),(.010,.016),(.014,.015)],mat,(x+.214,y+sign*.024,z),(0,sign,0))

# Driver bits and maintenance bottle at the outer end of the short wing.
holder=box('Six bit holder',(-1.04,-.90,top+.017),(.065,.19,.03),'GW3_Rubber',.005)
for i in range(6):
    q=(-1.04,-.975+i*.03,top+.024)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0053,depth=.019,location=(q[0],q[1],top+.029))
    cutter=bpy.context.object;active(holder);cut=holder.modifiers.new('Recessed bit socket','BOOLEAN');cut.operation='DIFFERENCE';cut.object=cutter
    bpy.ops.object.modifier_apply(modifier=cut.name);bpy.data.objects.remove(cutter,do_unlink=True)
    lathe('Driver bit '+str(i+1),[(0,.004),(.014,.004),(.022,.0025),(.025,.0025)],'GW3_Steel',q,segments=6 if i%2 else 24)
    if i%3==0:box('Slotted bit blade',(q[0],q[1],q[2]+.030),(.0048,.001,.01),'GW3_DarkSteel',.0002)
    elif i%3==1:
        for size in [(.0046,.0011,.008),(.0011,.0046,.008)]:box('Cross drive bit',(q[0],q[1],q[2]+.029),size,'GW3_DarkSteel',.0002)
    else:cylinder('Hex drive bit',(q[0],q[1],q[2]+.023),(q[0],q[1],q[2]+.034),.0024,'GW3_DarkSteel',6)
    lathe('Bit socket collar',[(0,.005),(.0015,.005),(.002,.0045)],'GW3_DarkSteel',(q[0],q[1],top+.031),segments=32)
x,y=-1.04,-1.16
lathe('Amber maintenance bottle',[(0,.001),(0,.025),(.006,.029),(.075,.029),(.089,.022),(.10,.013),(.106,.013)],'GW3_Amber',(x,y,top+.002),segments=64)
lathe('Ribbed bottle cap',[(0,.015),(.004,.016),(.025,.016),(.028,.012)],'GW3_Rubber',(x,y,top+.105),segments=144,flutes=24)
lathe('Bottle dispensing nozzle',[(0,.006),(.015,.004),(.035,.0018)],'GW3_DarkSteel',(x,y,top+.132),segments=32)

# Curved paper label follows the bottle surface; readable marking is in its map.
verts=[];faces=[];segments=48
for z in [top+.026,top+.073]:
    for i in range(segments+1):
        a=-math.pi*.96+i/segments*math.pi*1.92
        verts.append((x+.02918*math.cos(a),y+.02918*math.sin(a),z))
for i in range(segments):faces.append((i,i+1,i+1+segments+1,i+segments+1))
me=bpy.data.meshes.new('Maintenance label');me.from_pydata(verts,[],faces);me.update();uv=me.uv_layers.new(name='UVMap')
for f in me.polygons:
    i=f.index
    for li,co in zip(f.loop_indices,[(i/segments,0),((i+1)/segments,0),((i+1)/segments,1),(i/segments,1)]):uv.data[li].uv=co
    f.use_smooth=True
o=bpy.data.objects.new('Curved maintenance label',me);bpy.context.scene.collection.objects.link(o);finish(o,o.name,'GW3_Label');o['turned_surface']=True

# Reuse the already authored lamp and its matching flex cable, as requested.
KIT=PROJECT/'SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonWorkbenchKit.blend'
lamp_names=['SM_WBK_Bench_TaskLamp','SM_WBK_LampFlex']
with bpy.data.libraries.load(str(KIT),link=False) as (src,dst):dst.objects=lamp_names
shift=Matrix.Translation(Vector((1.035,1.105,top))-Vector((-.27,-.65,.939)))
for obj,ratio in zip(dst.objects,[.55,.65]):
    if obj is None:raise RuntimeError('Existing lamp component is missing')
    bpy.context.scene.collection.objects.link(obj);obj.hide_set(False)
    bpy.context.view_layer.update()
    source_transform=obj.matrix_world.copy()
    obj.parent=None
    obj.matrix_world=shift@source_transform
    active(obj);modifier=obj.modifiers.new('Existing buildable lamp budget','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj['keep_source_uv']=True
    parts.append(obj)

# Keep editable separate components, then export one joined copy for stable prefab use.
for o in parts:
    active(o)
    if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
    if o!=base and not o.get('keep_source_uv'):
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if o.name=='Silicone mat' or o.name.startswith('Magnetic dish'):
            size=Vector(o.dimensions);uv=o.data.uv_layers.active
            for f in o.data.polygons:
                for li in f.loop_indices:
                    co=o.data.vertices[o.data.loops[li].vertex_index].co
                    uv.data[li].uv=(.5+co.x/max(size.x,.001),.5+co.y/max(size.y,.001))
        elif not o.get('turned_surface'):
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
# Attach the matching PBR maps to the editable material source too.
exec(compile((PROJECT/'Tools/GunWorkbench/bind_polish_surfaces.py').read_text(encoding='utf-8'), 'bind_polish_surfaces.py', 'exec'))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GunWorkbench_Editable.blend'))
copies=[]
for o in parts:
    c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in copies:c.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();merged=copies[0];merged.name='SM_GunWorkbench'
tri=merged.modifiers.new('FBX triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
active(merged)
fbx=OUT/'SM_GunWorkbench.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
manifest={'fbx':str(fbx),'source_table':str(SOURCE),'reference':str(PROJECT/'SourceAssets/GunWorkbench20260928/Reference/workbench-reference.png'),'triangles':len(merged.data.polygons),'new_materials':SPEC,'weapon_material_slots':{},'retained':'original wood top and steel frame; existing lamp component reused at rear corner','new_props':['silicone mat','existing Bench_TaskLamp + LampFlex (repositioned)','2 spun magnetic dishes','3 pin punches','precision driver','nylon brass mallet','6 bit holder','maintenance bottle'],'tests_run':False,'renders_run':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('GUN_WORKBENCH_POLISH_AUTHORED '+str(fbx))
