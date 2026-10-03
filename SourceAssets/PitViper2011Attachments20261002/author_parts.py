"""Fit existing common pistol accessories to the actual Pit Viper surfaces."""
import bpy, bmesh, json, math, re
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent
S = O.parent
C = S / 'PitViper2011Integration20261002'
E = O / 'Exports'
E.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
auth = json.loads((C / 'Single/authoring.json').read_text())
alignment = Matrix(auth['alignment'])
raw = json.loads((C / 'canonical_parts.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(C / 'Single/PitViper2011_single_Editable.blend'))
rig = bpy.data.objects['SK_PitViper2011_Manny']
root = rig.data.bones['WPN_root'].matrix_local.copy()
rinv = root.inverted()
records = {}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active = ob

def source_bvh(parts):
    vertices = []; faces = []
    for part in parts:
        offset = len(vertices)
        vertices.extend(alignment @ Vector(v) for v in part['verts'])
        faces.extend([offset + i for i in p] for p in part['faces'])
    return BVHTree.FromPolygons(vertices, faces)

slide = source_bvh([p for p in raw if p['identity'] == '2011pv slide_1' and p['material'] == 'h-190'])
frame = source_bvh([p for p in raw if p['identity'] == '2011pv frame_12' and p['material'] == 'h-190'])
grip = source_bvh([p for p in raw if p['identity'] == '2011pv frame_12' and p['material'] == 'polymer'])
rear = alignment @ Vector(auth['markers_source_m']['WPN_RearSight'])
optic_origin = rear + Vector((0, -.016, .0045))
canonical_frame = Matrix(((0,-1,0,0),(1,0,0,0),(0,0,1,0),(0,0,0,1)))

def metal(name='M_PitViper2011_Adapter'):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)

def physical_uv(ob):
    while len(ob.data.uv_layers) < 4:
        ob.data.uv_layers.new(name='UV' + str(len(ob.data.uv_layers)))
    for layer in list(ob.data.uv_layers)[1:]:
        for face in ob.data.polygons:
            axes = [i for i in range(3) if i != max(range(3), key=lambda k: abs(face.normal[k]))]
            for li in face.loop_indices:
                p = ob.data.vertices[ob.data.loops[li].vertex_index].co
                layer.data[li].uv = (p[axes[0]]/.1, p[axes[1]]/.1)

def new_mesh(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces); mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    ob = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(ob)
    mesh.materials.append(material); mesh.uv_layers.new(name='UV0'); physical_uv(ob)
    return ob

def join(ob, extra):
    for part in [ob] + extra:
        physical_uv(part)
        for i, layer in enumerate(part.data.uv_layers): layer.name = 'UV' + str(i)
    select(ob)
    for part in extra: part.select_set(True)
    if extra: bpy.ops.object.join()
    return ob

def add_socket(ob, name, point):
    child = next((c for c in ob.children if c.name.removeprefix('SOCKET_') == name), None)
    if not child:
        child = bpy.data.objects.new('SOCKET_' + name, None); bpy.context.collection.objects.link(child); child.parent = ob
    child.location = Vector(point)
    return child

def export(ob, key, details):
    ob.name = 'SM_PitViper2011_' + key
    select(ob)
    sockets = {}
    for child in ob.children:
        if child.type == 'EMPTY':
            child.select_set(True); sockets[re.sub(r'\.\d{3}$', '', child.name.removeprefix('SOCKET_'))] = list(child.location)
    physical_uv(ob)
    file = E / (ob.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True, object_types={'MESH','EMPTY'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=False,
        mesh_smooth_type='FACE', use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(E / (ob.name + '_Editable.blend')))
    records[key] = dict(details, fbx=str(file), name=ob.name,
        materials=[m.name for m in ob.data.materials], sockets_blender_m=sockets, runtime_tested=False)
    (O / 'authoring.json').write_text(json.dumps(records, indent=2), encoding='utf8')
    print('PIT_VIPER_PART_AUTHORED', key, flush=True)

# Retain the feed interface and hand contact section; extend only the exposed
# straight shell below the grip along its measured front/back section tangent.
mag_parts = [p for p in raw if p['identity'].startswith('919 2011 15rnd mag empty')]
steel = next(p for p in mag_parts if p['material'] == 'stell')
steel_vertices = [alignment @ Vector(v) for v in steel['verts']]
def section_center(z):
    near = sorted(steel_vertices, key=lambda v: abs(v.z-z))[:80]
    return sum(near, Vector()) / len(near)
bottom = min(v.z for v in steel_vertices)
axis = (section_center(bottom+.013) - section_center(bottom+.060)).normalized()
extension = axis * .018
cut = bottom + .011
vertices=[]; faces=[]; corner_uv=[]; materials=[]
def clip(poly, above):
    result=[]
    for a,b in zip(poly, poly[1:]+poly[:1]):
        da=a[0].z-cut; db=b[0].z-cut
        ia=da>=-1e-8 if above else da<=1e-8; ib=db>=-1e-8 if above else db<=1e-8
        if ia: result.append(a)
        if ia!=ib:
            t=da/(da-db); result.append((a[0].lerp(b[0],t), a[1].lerp(b[1],t)))
    return result
def emit(poly, mi, shift=Vector()):
    if len(poly)<3: return
    start=len(vertices); vertices.extend(root @ (p+shift) for p,uv in poly)
    faces.append(tuple(range(start,len(vertices)))); corner_uv.append([uv for p,uv in poly]); materials.append(mi)
for mi,part in enumerate(mag_parts):
    cursor=0
    for face in part['faces']:
        poly=[(alignment @ Vector(part['verts'][vi]), Vector(part['uv'][cursor+i])) for i,vi in enumerate(face)]
        cursor+=len(face)
        upper=clip(poly,True); lower=clip(poly,False); emit(upper,mi); emit(lower,mi,extension)
        cuts=[p for p in upper if abs(p[0].z-cut)<1e-7]
        if len(cuts)==2:
            a,b=cuts
            # This author's shell is plain coated steel at the cut: no ribs or
            # lettering cross the extension. The original contour defines it.
            emit([a,b,(b[0]+extension,b[1]),(a[0]+extension,a[1])],mi)
mesh=bpy.data.meshes.new('PitViper2011_NativeExtendedMagazine'); mesh.from_pydata(vertices,[],faces); mesh.update()
uv=mesh.uv_layers.new(name='UV0')
for f,coords,mi in zip(mesh.polygons,corner_uv,materials):
    f.material_index=mi
    for li,value in zip(f.loop_indices,coords): uv.data[li].uv=value
for part in mag_parts: mesh.materials.append(metal('M_PitViper2011_Magazine_'+part['material']))
bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
ext=bpy.data.objects.new('NativeExtendedMagazine',mesh); bpy.context.collection.objects.link(ext)
export(ext,'ext_mag',dict(source=str(C/'canonical_parts.json'), frame='native unchanged skeletal component reference',
    extension_m=list(extension), cut_root_z_m=cut, capacity=18, preserved='feed, latch, grip-contact region, original steel/polymer split'))

# GripSurface is produced by the longitudinal author called at the end. Do not
# recreate a superseded short surface among this batch's other accessory files.

sources = {
 'holographic': S/'G18AttachmentRepair20260930/Exports/SM_G18_holographic_Editable.blend',
 'panoramic_red_dot': S/'G18AttachmentRepair20260930/Exports/SM_G18_panoramic_red_dot_Editable.blend',
 'eoth_holographic': S/'EOTHReticle20261001/Exports/SM_M1911_eoth_holographic.fbx',
 'suppressor': S/'M1911CompactFit20260913/FBX/suppressor.fbx',
 'tactical_suppressor': S/'ReferenceSuppressor5080_20260913/GameIntegration/M1911/SM_TacticalSuppressor.fbx',
 'brake': S/'M1911MuzzleRedDot20260913/SM_M1911_brake.fbx',
 'multi_caliber_suppressor': S/'HK416UniversalParts20260930/Exports/SM_Pistol_multi_caliber_suppressor.fbx',
 'laser': S/'M1911CompactFit20260913/laser/SM_TacticalDevice.fbx',
 'flashlight': S/'M1911CompactFit20260913/flashlight/SM_TacticalDevice.fbx'}

def load_source(file):
    if file.suffix=='.blend': bpy.ops.wm.open_mainfile(filepath=str(file))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=str(file))
    objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith(('SM_G18','SM_M1911','SM_Tactical','SM_Pistol'))]
    if not objects: objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
    ob=objects[0]; select(ob)
    for part in objects:
        part.hide_set(False); part.select_set(True)
    if len(objects)>1: bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return ob

def remove_adapter(ob):
    adapter={i for i,m in enumerate(ob.data.materials) if any(s in m.name.lower() for s in ('adapter','attachmentfinish','interfacesteel','tactical_collar'))}
    bm=bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in adapter],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS'); bm.to_mesh(ob.data); bm.free()

def sampled_shell(name,nx,ny,point_a,point_b):
    vertices=[]; faces=[]
    for fn in (point_a,point_b):
        vertices.extend(fn(i/nx,j/ny) for i in range(nx+1) for j in range(ny+1))
    count=(nx+1)*(ny+1); ix=lambda i,j:i*(ny+1)+j
    for i in range(nx):
        for j in range(ny):
            f=(ix(i,j),ix(i+1,j),ix(i+1,j+1),ix(i,j+1)); faces.extend([f,tuple(v+count for v in f[::-1])])
    edge=[ix(i,0) for i in range(nx)]+[ix(nx,j) for j in range(ny)]+[ix(i,ny) for i in range(nx,0,-1)]+[ix(0,j) for j in range(ny,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]): faces.append((a,a+count,b+count,b))
    return new_mesh(name,vertices,faces,metal())

for key,file in sources.items():
    ob=load_source(file)
    details=dict(source=str(file))
    if key in ('holographic','panoramic_red_dot','eoth_holographic'):
        remove_adapter(ob)
        foot=BVHTree.FromPolygons([v.co for v in ob.data.vertices],
            [list(f.vertices) for f in ob.data.polygons if 'reticle' not in ob.data.materials[f.material_index].name.lower()
             and 'glass' not in ob.data.materials[f.material_index].name.lower()])
        xmin,xmax=-.003,.013; half=.007 if key=='panoramic_red_dot' else .010
        def bottom_surface(u,v):
            x=xmin+(xmax-xmin)*u; y=half*(v*2-1)
            hit=slide.ray_cast(Vector((-y,optic_origin.y-x,.15)),Vector((0,0,-1)))[0]
            if hit is None: raise RuntimeError('Missing Pit Viper slide seat')
            return (x,y,hit.z-optic_origin.z-.00012)
        def top_surface(u,v):
            x=xmin+(xmax-xmin)*u; y=half*(v*2-1)
            hit=foot.ray_cast(Vector((x,y,-.10)),Vector((0,0,1)))[0]
            if hit is None: raise RuntimeError('Missing optic foot '+key+' '+str((x,y)))
            return (x,y,hit.z+.00012)
        saddle=sampled_shell('PitViper_ProfiledSlideSeat',12,10,bottom_surface,top_surface)
        join(ob,[saddle])
        if key=='holographic': aim=Vector((-.00653782,0,.05175324))*.62
        elif key=='panoramic_red_dot': aim=Vector((.02125,0,.0325))*.62
        else: aim=next(c.location.copy() for c in ob.children if c.name.startswith('SOCKET_SightRear'))
        add_socket(ob,'AimCenter',aim)
        add_socket(ob,'SightRear',aim); add_socket(ob,'SightFront',aim+Vector((.03,0,0))); add_socket(ob,'SightUp',aim+Vector((0,0,.03)))
        details.update(frame='+X forward, +Z up; native slide mount', mount_origin_root_m=list(optic_origin),
            adapter='closed shell sampled between actual slide roof and retained optic foot', optical_body_uv0_preserved=True)
    elif key in ('laser','flashlight'):
        remove_adapter(ob)
        # Separate the source's explicitly marked metal faces from its rubber,
        # aperture and lenses. These faces receive the current gun's WS parent;
        # the retained source optical shader and UV0 remain on the other faces.
        region = ob.data.color_attributes.get('MetalRegion')
        if region is None: raise RuntimeError('Missing tactical material region '+key)
        metal_slot = len(ob.data.materials)
        ob.data.materials.append(metal('M_PitViper2011_TacticalMetal'))
        for face in ob.data.polygons:
            if all(region.data[li].color[0] >= .5 for li in face.loop_indices):
                face.material_index = metal_slot
        # Source devices are already pistol-sized. Carry optics and emission
        # points by the same translation; rebuild only the fitted rail seat.
        top=max(v.co.z for v in ob.data.vertices)
        rail_y=-.077+alignment.translation.y
        rail=frame.ray_cast(Vector((0,rail_y,-.15)),Vector((0,0,1)))[0]
        if rail is None: raise RuntimeError('Missing native underside mounting surface')
        delta=Vector((0,rail_y+.083,rail.z-top-.004))
        ob.data.transform(Matrix.Translation(delta))
        for child in ob.children:
            if child.type=='EMPTY': child.location+=delta
        device=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons])
        def upper(u,v):
            x=(u-.5)*.015; y=rail_y+(v-.5)*.022
            hit=frame.ray_cast(Vector((x,y,-.15)),Vector((0,0,1)))[0]
            if hit is None: raise RuntimeError('Missing underside contact '+key)
            return (x,y,hit.z+.00012)
        def lower(u,v):
            x=(u-.5)*.015; y=rail_y+(v-.5)*.022
            hit=device.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)))[0]
            if hit is None: raise RuntimeError('Missing device shoulder '+key)
            return (x,y,hit.z-.00012)
        saddle=sampled_shell('PitViper_UnderRailSeat',8,10,upper,lower)
        join(ob,[saddle]); ob.data.transform(canonical_frame)
        for child in ob.children:
            if child.type=='EMPTY': child.location=canonical_frame@child.location
        details.update(frame='+X forward, +Z up; native root mount', rail_root_m=list(rail),
            adapter='closed shell between sampled frame underside and retained device body')
    else:
        # Old cans use Blender +Y / UE -Y. Author all new Pit Viper cans in
        # canonical +X so the outlet and axis are taken from explicit sockets.
        if key!='multi_caliber_suppressor':
            rotation=Matrix.Rotation(-math.pi/2,4,'Z')
            ob.data.transform(rotation)
            for child in ob.children:
                if child.type=='EMPTY': child.location=rotation@child.location
        forward=max(v.co.x for v in ob.data.vertices)
        add_socket(ob,'Muzzle',(forward,0,0)); add_socket(ob,'AimGuide',(forward+.04,0,0))
        details.update(frame='+X bore axis; inlet at model origin; mounted on actual compensator outlet',
            outlet_m=[forward,0,0], source_uv0_preserved=True)
    export(ob,key,details)

print('PIT_VIPER_ATTACHMENTS_SOURCE_SAVED',len(records),flush=True)
repair=S/'PitViper2011OpticPreviewFix20261002/author_optics.py'
if repair.exists():
    exec(compile(repair.read_text(encoding='utf8'),str(repair),'exec'),{'__file__':str(repair),'__name__':'__main__'})
# Preserve the current full-height grip-body domain when authoring the whole
# accessory set. This replaces only GripSurface in the authoring record.
common_longitudinal=Path(__file__).parent.parent/'PitViper2011CommonLongitudinalGrips20261003/author_grip.py'
if common_longitudinal.exists():
    import runpy
    runpy.run_path(str(common_longitudinal),run_name='__main__')
