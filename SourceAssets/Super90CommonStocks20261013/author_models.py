"""Preserve the native front stock neck, then connect common stocks with a closed rod.

Only static derivatives are cut. The production skinned mesh receives material
groups later: its vertices, weights, skeleton, UVs and animations are untouched.
"""
import bpy,bmesh,json,gzip,math,sys,collections
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.geometry import convex_hull_2d
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'HK416CommonAttachments20260930'))
from reargrip_interfaces import remember_normals,restore_normals
bpy.context.preferences.filepaths.save_version=0
with gzip.open(O/'Inputs/native_geometry.json.gz','rt') as f: native=json.load(f)
C=json.loads((O/'inputs.json').read_text())
D=O/'Meshes';D.mkdir(exist_ok=True)
CUT=-.225
ANGLE=math.radians(6)
REAR=Vector((0,-math.cos(ANGLE),-math.sin(ANGLE)))
UP=Vector((0,-math.sin(ANGLE),math.cos(ANGLE)))
ROT=Matrix((REAR,Vector((1,0,0)),UP)).transposed().to_4x4()
ORIGIN=Vector((0,CUT,-.7749))

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]

def imported(key):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')),use_anim=False)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    return ob

def project_new_uv(mesh,faces):
    if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
    for f in faces:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
        for li in f.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            mesh.uv_layers[0].data[li].uv=(co[axes[0]]/.04,co[axes[1]]/.04)

# A coordinate threshold also catches 120 trigger-guard triangles. Follow the
# stock's connected polymer island, seeded at the shoulder, within this material.
positions=native['positions'];triangles=native['triangles'];materials=native['materials']
keys=[tuple(round(c,4) for c in p) for p in positions];adj=collections.defaultdict(list)
for i,tri in enumerate(triangles):
    if materials[i]==10:
        for j in tri:adj[keys[j]].append(i)
seed=next(i for i,tri in enumerate(triangles) if materials[i]==10 and all(positions[j][1]>40 for j in tri))
stock_polymer={seed};todo=[seed]
while todo:
    for j in triangles[todo.pop()]:
        for i in adj[keys[j]]:
            if i not in stock_polymer:stock_polymer.add(i);todo.append(i)
if len(stock_polymer)!=2390:raise RuntimeError('Stock polymer island changed; remeasure native source')
factory=list(stock_polymer)
for i,(tri,mat) in enumerate(zip(native['triangles'],native['materials'])):
    yy=[native['positions'][j][1] for j in tri]
    if mat in (4,9) and min(yy)>30:factory.append(i)
factory.sort()
(O/'factory_triangles.json').write_text(json.dumps(factory))
body=imported('super90')
# FBX export uses current material objects as names, but retains slot ordering.
stock_poly=next(i for i,m in enumerate(body.data.materials) if m.name=='MI_Super90_S90_Polymer')
stock_rubber=next(i for i,m in enumerate(body.data.materials) if m.name=='MI_Super90_S90_Rubber')
stock_receiver=next(i for i,m in enumerate(body.data.materials) if m.name=='MI_Super90_TTI_Benelli_M4')
remember_normals(body.data)
bm=bmesh.new();bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
seed=next(f for f in bm.faces if f.material_index==stock_poly and all(v.co.y<-.4 for v in f.verts))
# Seam-split FBX vertices are matched by position while retaining all attributes.
links=collections.defaultdict(list)
for f in bm.faces:
    if f.material_index==stock_poly:
        for v in f.verts:links[tuple(round(c,6) for c in v.co)].append(f)
poly={seed};todo=[seed]
while todo:
    for v in todo.pop().verts:
        for f in links[tuple(round(c,6) for c in v.co)]:
            if f not in poly:poly.add(f);todo.append(f)
if len(poly)!=2390:raise RuntimeError('FBX stock island differs from production source')
keep=poly|{f for f in bm.faces if f.material_index in (stock_receiver,stock_rubber) and max(v.co.y for v in f.verts)<-.30}
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f not in keep],context='FACES')
bm.to_mesh(body.data);bm.free();restore_normals(body.data)
body.name='Super90_FactoryStock'
bpy.data.libraries.write(str(O/'FactoryStock.blend'),{body},fake_user=True)

# Retain the original front neck and mating web exactly. Rebuild only its rear cut.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=stock_poly],context='FACES')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
    plane_co=(0,CUT,0),plane_no=(0,1,0),clear_inner=True,clear_outer=False)
bm.to_mesh(body.data);bm.free();restore_normals(body.data)
old=body.data
bm=bmesh.new();bm.from_mesh(old);bm.verts.ensure_lookup_table()
edges={e for e in bm.edges if e.is_boundary and all(abs(v.co.y-CUT)<1e-6 for v in e.verts)}
if not edges:raise RuntimeError('Native stock cut has no boundary')
edge=edges.pop();first=edge.verts[0];v=edge.verts[1];ring=[first.index,v.index]
while v!=first:
    candidates=[e for e in v.link_edges if e in edges]
    if len(candidates)!=1:raise RuntimeError('Native stock cut boundary is not a single loop')
    edge=candidates[0];edges.remove(edge);v=edge.other_vert(v)
    if v!=first:ring.append(v.index)
if edges:raise RuntimeError('Multiple native stock cut loops')
bm.free()
points=[v.co.copy() for v in old.vertices]
faces=[tuple(f.vertices) for f in old.polygons]
uvs=[[tuple(d.uv) for d in layer.data] for layer in old.uv_layers]
normals=[tuple(n.vector) for n in old.corner_normals]
native_count=len(faces)
center=sum((points[i] for i in ring),Vector())/len(ring)
# Keep the rim order; circular stations use each real rim point's radial angle.
angles=[math.atan2(points[i].z-ORIGIN.z,points[i].x) for i in ring]
previous=ring
for distance,radius,mix in [(.003,.015,0.2),(.010,.0137,.8),(.020,.0116,1.0)]:
    current=[]
    for source,angle in zip(ring,angles):
        p=ORIGIN+REAR*distance+Vector((math.cos(angle),0,0))*radius+UP*(math.sin(angle)*radius)
        q=points[source]+REAR*distance
        current.append(len(points));points.append(q.lerp(p,mix))
    faces.extend((previous[j],previous[(j+1)%len(ring)],current[(j+1)%len(ring)],current[j]) for j in range(len(ring)))
    previous=current
faces.append(tuple(reversed(previous)))
mesh=bpy.data.meshes.new('Super90_NativeStockNeck');mesh.from_pydata(points,[],faces);mesh.update()
mesh.materials.append(bpy.data.materials.new('S90_StockNativePolymer'))
mesh.materials.append(bpy.data.materials.new('S90_StockAdapterMetal'))
for k,layer in enumerate(uvs):
    out=mesh.uv_layers.new(name=old.uv_layers[k].name)
    for j,value in enumerate(layer):out.data[j].uv=value
for f in mesh.polygons:f.material_index=0 if f.index<native_count else 1;f.use_smooth=True
project_new_uv(mesh,list(mesh.polygons)[native_count:])
# Recalculate the new transition, while keeping source normals on retained faces.
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
mesh.normals_split_custom_set(normals+[(0,0,0)]*(len(mesh.loops)-len(normals)))
body.data=mesh;body.name='Super90_NativeStockNeck'
bpy.data.libraries.write(str(O/'NativeStockNeck.blend'),{body},fake_user=True)
report={'frame':'Native Super90 component bind metres; FBX cm, full WPN_root bind inverse at runtime',
    'factory_faces':len(factory),'native_cut_y_m':CUT,'rod_diameter_m':.0232,'rod_down_angle_deg':6,
    'parts':{},'runtime_tested':False}

def cylinder(name,start,end,radius,material):
    axis=end-start
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=axis.length,location=(start+end)*.5)
    ob=bpy.context.object;ob.name=name;ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(axis.normalized())
    ob.data.materials.append(material);select([ob]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=ob.modifiers.new('Machined edges','BEVEL');mod.width=.0003;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=ob.modifiers.new('Face normals','WEIGHTED_NORMAL');bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);project_new_uv(ob.data,ob.data.polygons)
    return ob

def stock_socket(body,transform,material):
    """Close the real donor mouth and taper its outline to the connection rod."""
    cut=min(v.co.x for v in body.data.vertices)+.0015
    crossings=[]
    for e in body.data.edges:
        a,b=[body.data.vertices[i].co for i in e.vertices]
        if (a.x-cut)*(b.x-cut)<0:
            p=a.lerp(b,(cut-a.x)/(b.x-a.x));crossings.append(Vector((p.y,p.z)))
    if len(crossings)<3:raise RuntimeError('Missing stock socket outline')
    outline=[crossings[i] for i in convex_hull_2d(crossings)]
    center=Vector(((min(p.x for p in outline)+max(p.x for p in outline))*.5,(min(p.y for p in outline)+max(p.y for p in outline))*.5))
    count=64;profile=[]
    cross=lambda a,b:a.x*b.y-a.y*b.x
    for j in range(count):
        angle=math.tau*j/count;ray=Vector((math.cos(angle),math.sin(angle)));dist=[]
        for a,b in zip(outline,outline[1:]+outline[:1]):
            edge=b-a;den=cross(ray,edge)
            if abs(den)<1e-12:continue
            t=cross(a-center,edge)/den;u=cross(a-center,ray)/den
            if t>0 and -.00001<=u<=1.00001:dist.append(t)
        if not dist:raise RuntimeError('Stock socket outline cannot be sampled')
        profile.append(center+ray*max(dist))
    remember_normals(body.data);bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
        plane_co=(cut,0,0),plane_no=(1,0,0),clear_inner=True,clear_outer=False)
    bm.to_mesh(body.data);bm.free();restore_normals(body.data)
    verts=[];faces=[]
    for level in range(4):
        t=level/3;s=t*t*(3-2*t)
        for j,p in enumerate(profile):
            angle=math.tau*j/count
            a=Vector((cut-.009,math.cos(angle)*.0116,math.sin(angle)*.0116))
            b=Vector((cut+.0002,p.x,p.y));v=a.lerp(b,s)
            v.x=(cut-.009)*(1-t)+(cut+.0002)*t
            verts.append(transform@v)
    for level in range(3):
        faces.extend((level*count+j,level*count+(j+1)%count,(level+1)*count+(j+1)%count,(level+1)*count+j) for j in range(count))
    faces.extend([tuple(range(count-1,-1,-1)),tuple(range(3*count,4*count))])
    me=bpy.data.meshes.new('StockSocketTransition');me.from_pydata(verts,[],faces);me.update();me.materials.append(material)
    ob=bpy.data.objects.new('StockSocketTransition',me);bpy.context.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for f in me.polygons:f.use_smooth=len(f.vertices)==4
    project_new_uv(me,me.polygons)
    return ob,{'donor_mouth_x_m':cut,'width_m':max(p.x for p in profile)-min(p.x for p in profile),'height_m':max(p.y for p in profile)-min(p.y for p in profile)}

for key in ('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'):
    donor=imported(key)
    slots=C['assets'][key]['slots']
    bindings={}
    for i,m in enumerate(donor.data.materials):
        m.name='S90_Stock_'+key+'_'+str(i)
        bindings[m.name]=slots[i]
    remember_normals(donor.data)
    if key in ('core_stock','tactical_telescopic'):
        # Remove the rifle's old receiver collar; the stock body's socket stays.
        bm=bmesh.new();bm.from_mesh(donor.data)
        remove=2 if key=='core_stock' else 3
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==remove],context='FACES')
        bm.to_mesh(donor.data);bm.free();restore_normals(donor.data)
    if key=='legendary_adjustable_tactical_stock':
        bm=bmesh.new();bm.from_mesh(donor.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
            plane_co=(0,.0735,0),plane_no=(0,1,0),clear_inner=True,clear_outer=False)
        rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-.0735)<1e-6 for v in e.verts)]
        bmesh.ops.holes_fill(bm,edges=rim,sides=0)
        bm.to_mesh(donor.data);bm.free();restore_normals(donor.data)
        # Undo only the known M4 fitting; retain the current V3 shoulder contour.
        canonical=Matrix(((0,1,0,-.0735),(-1,0,0,-.0000732),(0,0,1,-.075551152),(0,0,0,1)))
        donor.data.transform(canonical)
    # Keep each body at physical size. Place the buttpad at the original shoulder
    # plane, extending only the rod to accommodate different body lengths.
    extent=max(-(ROT@v.co).y for v in donor.data.vertices)
    distance=(.497+ORIGIN.y-extent)/math.cos(ANGLE)
    # The long adjustable body extends the shoulder plane instead of shortening
    # its accepted body or embedding its front inside the native grip web.
    distance=max(.040,distance)
    pivot=ORIGIN+REAR*distance
    transform=Matrix.Translation(pivot)@ROT
    with bpy.data.libraries.load(str(O/'NativeStockNeck.blend'),link=False) as (_,data):data.objects=['Super90_NativeStockNeck']
    neck=data.objects[0];bpy.context.collection.objects.link(neck)
    steel=next(m for m in neck.data.materials if m.name.startswith('S90_StockAdapterMetal'))
    socket,socket_info=stock_socket(donor,transform,steel)
    donor.data.transform(transform)
    rod=cylinder('S90_ConnectionRod',ORIGIN+REAR*.0195,pivot+REAR*.023,.0116,steel)
    lock=cylinder('S90_RodLockRing',ORIGIN+REAR*.021,ORIGIN+REAR*.027,.0133,steel)
    obs=[donor,neck,rod,lock,socket]
    bpy.ops.wm.save_as_mainfile(filepath=str(O/(key+'_Editable.blend')))
    select(obs);bpy.ops.object.join();part=bpy.context.object;part.name='SM_Super90_'+key
    part.data.uv_layers.active_index=0;part.data.uv_layers[0].active_render=True
    part.data.calc_loop_triangles()
    # Keep source UVs; only collapsed UV microfaces receive local planar UVs.
    invalid=[]
    for f in part.data.polygons:
        li=list(f.loop_indices)
        if len(li)!=3:continue
        a,b,c=[part.data.uv_layers[0].data[i].uv for i in li]
        if abs((b-a).cross(c-a))<1e-12:invalid.append(f)
    project_new_uv(part.data,invalid)
    areas={}
    for tri in part.data.loop_triangles:
        a,b,c=[part.data.uv_layers[0].data[i].uv for i in tri.loops]
        row=areas.setdefault(tri.material_index,[0.,0.]);row[0]+=tri.area*10000;row[1]+=abs((b-a).cross(c-a))*.5
    file=D/(part.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    report['parts'][key]={'file':str(file),'triangles':len(part.data.loop_triangles),'source':C['assets'][key]['path'],
        'bindings':bindings,'slots':[m.name for m in part.data.materials],'pivot_m':list(pivot),'rigid_transform':[list(r) for r in transform],
        'rod_length_m':distance+.023-.0195,'shoulder_y_m':-pivot.y+extent,'source_body_scale':1,'socket':socket_info,'area_cm2_uv':areas,'collapsed_uv_faces_repaired':len(invalid)}
    print('SUPER90_STOCK_AUTHORED',key,report['parts'][key]['triangles'],flush=True)
(O/'models.json').write_text(json.dumps(report,indent=2))
