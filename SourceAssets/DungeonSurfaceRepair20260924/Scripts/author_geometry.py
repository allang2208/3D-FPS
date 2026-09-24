"""Repair contact surfaces only, using original FBX geometry and UVs. No scene render."""
import hashlib,json,math,shutil
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored'
targets=json.loads((ROOT/'Config/geometry-targets.json').read_text())
receipt_path=ROOT/'Receipts/geometry.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(stage='authoring',meshes={},runtime_tested=False)

def frame_components(mesh):
    # Find authored disconnected solids without welding or rebuilding the mesh.
    parent=list(range(len(mesh.vertices)));positions={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(a,b):parent[find(a)]=find(b)
    for v in mesh.vertices:
        key=tuple(round(x,6) for x in v.co)
        if key in positions:join(v.index,positions[key])
        else:positions[key]=v.index
    for edge in mesh.edges:join(*edge.vertices)
    result={}
    for i in range(len(mesh.vertices)):result.setdefault(find(i),[]).append(i)
    return list(result.values())

def port_axes(port):
    p=Vector((port['position'][0]/100,-port['position'][1]/100,port['position'][2]/100))
    n=Vector((port['normal'][0],-port['normal'][1],port['normal'][2]));r=Vector((-n.y,n.x,0))
    return p,n,r,port.get('width',300)/100,port.get('height',280)/100

for item in targets:
    path=item['path']
    previous=receipt['meshes'].get(path)
    if previous and (previous.get('revision',1)>=4 or item['operation']!='portal_shell'):continue
    source=Path(item['source']);input_source=Path(previous['original']) if previous else source
    if previous and source.read_bytes()!=Path(previous['fbx']).read_bytes():raise RuntimeError('Preserve updated source '+str(source))
    sha=hashlib.sha256(input_source.read_bytes()).hexdigest()
    if sha!=item['source_sha256']:raise RuntimeError('Preserve changed source '+str(source))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.import_scene.fbx(filepath=str(input_source),use_custom_normals=True)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if len(objects)!=1:raise RuntimeError('Expected one authored mesh '+str(source))
    ob=objects[0];bpy.context.view_layer.objects.active=ob
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    mesh=ob.data;before=len(mesh.polygons);operation=item['operation'];changed=0
    before_bounds=[list(map(min,zip(*(v.co for v in mesh.vertices)))),list(map(max,zip(*(v.co for v in mesh.vertices))))]
    if operation=='portal_frames':
        normals=[n.vector.copy() for n in mesh.corner_normals];modified={}
        for port in item['ports']:
            p,n,r,w,h=port_axes(port)
            for ids in frame_components(mesh):
                coords=[((mesh.vertices[i].co-p).dot(r),(mesh.vertices[i].co-p).dot(n),mesh.vertices[i].co.z-p.z) for i in ids]
                if max(d for t,d,z in coords)-min(d for t,d,z in coords)<.289:continue
                def on_frame(q):
                    t,d,z=q
                    return abs(d)<=.14501 and ((w/2-.00001<=abs(t)<=w/2+.07001 and -.00001<=z<=h+.00001) or
                        (abs(t)<=w/2+.07001 and h-.00001<=z<=h+.08001))
                if not all(on_frame(q) for q in coords):continue
                for i in ids:
                    v=mesh.vertices[i];v.co+=n*((v.co-p).dot(n)*(.16/.145-1));modified[i]=n
                changed+=1
        for loop in mesh.loops:
            n=modified.get(loop.vertex_index)
            if n is not None:normals[loop.index]=(normals[loop.index]-n*normals[loop.index].dot(n)*(1-.145/.16)).normalized()
        mesh.normals_split_custom_set(normals)
    elif operation=='portal_shell':
        # These shells are authored as intersecting box solids. Move only their
        # existing reveal edges, including the 5 mm bevel, rather than applying
        # a solid Boolean to the entire disconnected wall assembly. Topology,
        # corner UVs, material indices and custom normals remain intact.
        for port in item['ports']:
            p,n,r,w,h=port_axes(port)
            for vertex in mesh.vertices:
                relative=vertex.co-p;t=relative.dot(r);d=relative.dot(n);z=relative.z
                if abs(d)>.1201:continue
                if abs(abs(t)-w/2)<=.0051:
                    vertex.co+=r*(.06 if t>0 else -.06);changed+=1
                if not item['elbow'] and abs(t)<=w/2+.0051 and h-.0001<=z<=h+.0051:
                    vertex.co.z+=.07;changed+=1
        if item['elbow']:
            for vertex in mesh.vertices:vertex.co.z*=2.84/2.8
    else:
        normals=[n.vector.copy() for n in mesh.corner_normals]
        for vertex in mesh.vertices:
            if operation=='connector_shell':
                sign=1 if vertex.co.x>=0 else -1
                vertex.co.x=sign*(1.54+(abs(vertex.co.x)-1.50)*(.20/.24));vertex.co.z*=2.84/2.8
            elif operation=='connector_ceilings':vertex.co.z=2.84+(vertex.co.z-2.8)*(.14/.18)
            else:vertex.co.x+=.04*(1 if vertex.co.x>=0 else -1)
            changed+=1
        if operation in ('connector_shell','connector_ceilings'):
            for normal in normals:
                if operation=='connector_shell':normal.x/=.20/.24;normal.z/=2.84/2.8
                else:normal.z/=.14/.18
                normal.normalize()
        mesh.normals_split_custom_set(normals)
    if not changed:raise RuntimeError('No authored portal geometry matched '+path)
    mesh.update();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    out=OUT/(source.stem+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,
                             mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(source.stem+'.blend')))
    backup=ROOT/'Sources/BeforeFBX'/source.parent.parent.name/source.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    # Future imports read the repaired editable export. Original geometry stays
    # in BeforeFBX; future full authoring uses the updated common reveal rules.
    shutil.copy2(out,source)
    bounds=[list(map(min,zip(*(v.co for v in mesh.vertices)))),list(map(max,zip(*(v.co for v in mesh.vertices))))]
    receipt['meshes'][path]=dict(revision=4,operation=operation,fbx=str(out),original=str(backup),source_sha256=sha,
        changed_solids_or_vertices=changed,polygons_before=before,polygons_after=len(mesh.polygons),bounds_before=before_bounds,bounds_after=bounds)
    receipt_path.write_text(json.dumps(receipt,indent=2));print('SURFACE_GEOMETRY_SAVED',len(receipt['meshes']),len(targets),path,flush=True)
receipt['stage']='authored';receipt_path.write_text(json.dumps(receipt,indent=2))
