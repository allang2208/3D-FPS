"""Fit existing furniture to M870. Native gun mesh only gets reversible sections."""
import bpy,bmesh,json,gzip,math,sys,ast,collections
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.geometry import convex_hull_2d
O=Path(__file__).parent;S=O.parent;X=O/'Meshes';X.mkdir(exist_ok=True)
sys.path.insert(0,str(S/'HK416CommonAttachments20260930'))
from reargrip_interfaces import remember_normals,restore_normals
C=json.loads((O/'inputs.json').read_text());CUT=-.22
R={'parts':{},'stock_cut_y_m':CUT,'runtime_tested':False}
bpy.context.preferences.filepaths.save_version=0
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def imported(key):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')),use_anim=False)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    bindings={}
    for i,m in enumerate(ob.data.materials):
        name='M870_'+key+'_'+str(i);m.name=name;bindings[name]=C['assets'][key]['slots'][i]['material']
    return ob,bindings
def uv(mesh,faces):
    if not mesh.uv_layers:mesh.uv_layers.new(name='UVMap')
    for f in faces:
        axes=[j for j in range(3) if j!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for li in f.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;mesh.uv_layers[0].data[li].uv=(co[axes[0]]/.04,co[axes[1]]/.04)
project_new_uv=uv
# Reuse the accepted stock socket/rod construction, preserving donor dimensions.
tree=ast.parse((S/'Super90CommonStocks20261013/author_models.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cylinder','stock_socket')],type_ignores=[]),'<shared stock interfaces>','exec'))
steel=bpy.data.materials.new('M870_AdapterSteel')
STEEL='/Game/Weapons/M870/Optics20261016/Materials/M_M870_AdapterSteel'
POLY='/Game/Weapons/Super90/CommonStocks20261013/Materials/MI_Super90_StockNativePolymer'
def cut(ob,y,keep_front,cap=False):
    remember_normals(ob.data);bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,y,0),plane_no=(0,1,0),clear_inner=keep_front,clear_outer=not keep_front)
    if cap:
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-y)<1e-6 for v in e.verts)]
        faces=bmesh.ops.holes_fill(bm,edges=edges,sides=0).get('faces',[])
        for f in faces:f.material_index=0
    bm.to_mesh(ob.data);bm.free();restore_normals(ob.data)
def emit(key,obs,bindings,source):
    select(obs);bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_M870_'+key
    if key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
        # Folding the donor end collars into the native neck can collapse small
        # triangles. Remove those production remnants before tangent generation.
        remember_normals(ob.data);bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_area()<1e-13],context='FACES')
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();restore_normals(ob.data);ob.data.update()
        invalid=[]
        for f in ob.data.polygons:
            a,b,c=[ob.data.uv_layers[0].data[i].uv for i in f.loop_indices]
            if abs((b-a).cross(c-a))<1e-10:invalid.append(f)
        uv(ob.data,invalid)
    # Import native normals; new adapter faces have their own physical UVs.
    ob.data.calc_loop_triangles()
    bpy.data.libraries.write(str(X/(ob.name+'_Editable.blend')),{ob},fake_user=True)
    f=X/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    R['parts'][key]={'file':str(f),'source':source,'bindings':bindings,'slots':[m.name for m in ob.data.materials],'triangles':len(ob.data.loop_triangles)}
    (O/'models.json').write_text(json.dumps(R,indent=2));print('M870_FURNITURE_AUTHORED',key,flush=True)
def load_native(name):
    with bpy.data.libraries.load(str(O/'NativeFurniture.blend'),link=False) as (_,d):d.objects=[name]
    ob=d.objects[0];bpy.context.collection.objects.link(ob);return ob

# Locate only the connected stock and buttpad islands; arms/guard stay untouched.
ob,bindings=imported('m870');native_mat=next(i for i,m in enumerate(ob.data.materials) if 'OriginalSurface' in C['assets']['m870']['slots'][i]['material'])
remember_normals(ob.data);bm=bmesh.new();bm.from_mesh(ob.data)
links=collections.defaultdict(list)
for f in bm.faces:
    if f.material_index==native_mat:
        for v in f.verts:links[tuple(round(c,6) for c in v.co)].append(f)
keep={f for f in bm.faces if f.material_index==native_mat and any(v.co.y<-.445 for v in f.verts)};stack=list(keep)
while stack:
    for v in stack.pop().verts:
        for f in links[tuple(round(c,6) for c in v.co)]:
            if f not in keep:keep.add(f);stack.append(f)
points={tuple(round(c*100,4) for c in (v.co.x,-v.co.y,v.co.z)) for f in keep for v in f.verts}
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f not in keep],context='FACES');bm.to_mesh(ob.data);bm.free();restore_normals(ob.data)
with gzip.open(O/'Inputs/native_geometry.json.gz','rt') as f:native=json.load(f)
from mathutils.kdtree import KDTree
kd=KDTree(len(points))
for i,p in enumerate(points):kd.insert(p,i)
kd.balance();inside=[kd.find(p)[2]<.001 for p in native['positions']]
ids=[i for i,t in enumerate(native['triangles']) if all(inside[j] for j in t)]
(O/'factory_triangles.json').write_text(json.dumps(ids));R['factory_triangles']=len(ids)
ob.name='NativeFurniture';bpy.data.libraries.write(str(O/'NativeFurniture.blend'),{ob},fake_user=True)
native_bind={m.name:bindings[m.name] for m in ob.data.materials}
tail=ob.copy();tail.data=ob.data.copy();bpy.context.collection.objects.link(tail);cut(tail,CUT,False,True)
emit('factory_stock',[tail],native_bind,C['assets']['m870']['path'])
front=load_native('NativeFurniture');cut(front,CUT,True,True)
emit('factory_reargrip',[front],native_bind,C['assets']['m870']['path'])

# Original cross-sections define both real connector ends and traditional grip fit.
def section(y,count=96):
    pts=[]
    for e in ob.data.edges:
        a,b=[ob.data.vertices[i].co for i in e.vertices]
        if (a.y-y)*(b.y-y)<0:pts.append(a.lerp(b,(y-a.y)/(b.y-a.y)))
    hull=[pts[i] for i in convex_hull_2d([Vector((p.x,p.z)) for p in pts])]
    center=Vector(((min(p.x for p in hull)+max(p.x for p in hull))*.5,y,(min(p.z for p in hull)+max(p.z for p in hull))*.5))
    cross=lambda a,b:a.x*b.y-a.y*b.x
    result=[]
    for j in range(count):
        angle=math.tau*j/count;ray=Vector((math.cos(angle),math.sin(angle)));ts=[]
        for a,b in zip(hull,hull[1:]+hull[:1]):
            a=Vector((a.x-center.x,a.z-center.z));b=Vector((b.x-center.x,b.z-center.z));edge=b-a;den=cross(ray,edge)
            if abs(den)<1e-10:continue
            t=cross(a,edge)/den;u=cross(a,ray)/den
            if t>0 and -1e-6<=u<=1.000001:ts.append(t)
        p=center+Vector((ray.x,0,ray.y))*max(ts);result.append(p)
    return center,result
stations={str(y):[list(p) for p in section(y)[1]] for y in [-.166-i*.0005 for i in range(109)]}
center,rim=section(CUT);R['stock_rim_m']=[list(p) for p in rim]
# Keep the front native grip. A closed shoulder tapers to a 23.2 mm buffer rod.
rear=Vector((0,-math.cos(math.radians(6)),-math.sin(math.radians(6))));up=Vector((0,-math.sin(math.radians(6)),math.cos(math.radians(6))))
ROT=Matrix((rear,Vector((1,0,0)),up)).transposed().to_4x4();ORIGIN=center.copy()
def adapter():
    verts=[];faces=[];n=len(rim)
    for k in range(6):
        t=k/5;s=t*t*(3-2*t);d=.045*t
        for j,p in enumerate(rim):
            angle=math.tau*j/n;q=center+rear*d+Vector((math.cos(angle),0,0))*.0116+up*(math.sin(angle)*.0116)
            verts.append((p+rear*d).lerp(q,s))
    for k in range(5):faces.extend((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j) for j in range(n))
    faces.extend([tuple(range(n-1,-1,-1)),tuple(range(5*n,6*n))])
    me=bpy.data.meshes.new('ClosedStockShoulder');me.from_pydata(verts,[],faces);me.update();me.materials.append(bpy.data.materials.new('M870_AdapterSteel'));uv(me,me.polygons)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    out=bpy.data.objects.new('ClosedStockShoulder',me);bpy.context.collection.objects.link(out);return out
for key in ('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'):
    donor,bind=imported(key);remember_normals(donor.data)
    bm=bmesh.new();bm.from_mesh(donor.data)
    if key in ('core_stock','tactical_telescopic'):bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==(2 if key=='core_stock' else 3)],context='FACES')
    if key=='legendary_adjustable_tactical_stock':
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,.0735,0),plane_no=(0,1,0),clear_inner=True)
        bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-.0735)<1e-6 for v in e.verts)],sides=0)
    bm.to_mesh(donor.data);bm.free();restore_normals(donor.data)
    if key=='legendary_adjustable_tactical_stock':donor.data.transform(Matrix(((0,1,0,-.0735),(-1,0,0,-.0000732),(0,0,1,-.075551152),(0,0,0,1))))
    extent=max(-(ROT@v.co).y for v in donor.data.vertices);distance=max(.065,(.485+ORIGIN.y-extent)/(-rear.y));pivot=ORIGIN+rear*distance;transform=Matrix.Translation(pivot)@ROT
    steel=bpy.data.materials.new('M870_AdapterSteel');socket,info=stock_socket(donor,transform,steel);donor.data.transform(transform)
    rod=cylinder('M870_ConnectionRod',ORIGIN+rear*.044,pivot+rear*.023,.0116,steel)
    lock=cylinder('M870_RodLock',ORIGIN+rear*.046,ORIGIN+rear*.052,.0133,steel)
    neck=adapter();bind.update({m.name:STEEL for x in (socket,rod,lock,neck) for m in x.data.materials})
    emit(key,[donor,socket,rod,lock,neck],bind,C['assets'][key]['path'])
    R['parts'][key].update(body_scale=1,rod_length_m=distance-.044+.023,socket=info)

# Rear grips are produced by RearGripFinish/author.py after the other parts.

# Reuse accepted common foregrip bodies. Replace only the S90 saddle with a
# M870-specific seat following its actual pump underside surface.
mount=Matrix(((0,-1,0,0),(1,0,0,.213),(0,0,1,-.787),(0,0,0,1)))
R['foregrip_mount_blender']=[list(r) for r in mount];R['foregrip_bone']='WPN_bolt'
# Extract the pump underside from current source geometry for a seated clamp.
from mathutils.bvhtree import BVHTree
with bpy.data.libraries.load(str(O/'Inputs/Native_Edit.blend'),link=False) as (_,d):d.objects=['SK_M870_V7.001']
full=d.objects[0];pump_faces=[list(f.vertices) for f in full.data.polygons if all(.131<v.co.y<.296 and -.784<v.co.z<-.735 for v in (full.data.vertices[i] for i in f.vertices))]
pump_tree=BVHTree.FromPolygons([v.co.copy() for v in full.data.vertices],pump_faces,all_triangles=True)
for key in ('vertical','tactical_vertical','canted','prism','angled'):
    donor,bind=imported(key);old=C['assets'][key]['slots'];bm=bmesh.new();bm.from_mesh(donor.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if 'Saddle' in old[f.material_index]['name']],context='FACES');bm.to_mesh(donor.data);bm.free()
    # The pump bottom is a rounded 43.8 mm wide cross-section. Sampling original
    # fore-end triangles makes the top surface seat into its lowest ridges.
    native=load_native('NativeFurniture');bpy.data.objects.remove(native,do_unlink=True)
    verts=[];faces=[];n=13;count=n+2;rows=17
    for row in range(rows):
        x=-.052+.104*row/(rows-1)
        for j in range(n):
            y=-.0105+.021*j/(n-1);world=mount@Vector((x,y,0))
            hit,normal,idx,dist=pump_tree.ray_cast(Vector((world.x,world.y,-1)),Vector((0,0,1)),.3)
            if hit is None:raise RuntimeError('Pump contact missing at '+str((x,y)))
            z=hit.z-mount.translation.z+.00015
            verts.append((x,y,z))
        verts.extend([(x,.0105,0),(x,-.0105,0)])
    faces.extend([tuple(range(count-1,-1,-1)),tuple(range((rows-1)*count,rows*count))])
    for row in range(rows-1):faces.extend((row*count+j,row*count+(j+1)%count,(row+1)*count+(j+1)%count,(row+1)*count+j) for j in range(count))
    me=bpy.data.meshes.new('M870_PumpSeat');me.from_pydata(verts,[],faces);me.update();mat=bpy.data.materials.new('M870_AdapterSteel');me.materials.append(mat);uv(me,me.polygons)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    seat=bpy.data.objects.new('PumpSeat',me);bpy.context.collection.objects.link(seat)
    donor.data.transform(mount);seat.data.transform(mount);bind[mat.name]=STEEL
    emit(key,[donor,seat],bind,C['assets'][key]['path'])
(O/'models.json').write_text(json.dumps(R,indent=2));print('M870_FURNITURE_MODELS_COMPLETE',flush=True)

# Final production path for rear grips: continuous fitting and fresh corner normals.
import runpy
runpy.run_path(str(O/"RearGripFinish/author.py"))
