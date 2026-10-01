"""Fit the three approved M1911-style muzzle visuals to G18; titanium is excluded."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;X=O/'Exports';X.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
source=json.loads((O/'source_dimensions.json').read_text());record={};icons={}
front=[Vector(p) for p in source['gun']['front_vertices_root_m'] if p[1]<-.13195]
center=Vector(((min(p.x for p in front)+max(p.x for p in front))*.5,min(p.y for p in front),(min(p.z for p in front)+max(p.z for p in front))*.5))
marker=Vector(source['gun']['muzzle_marker_root_m'])
radii=[math.hypot(p.x-center.x,p.z-center.z) for p in front]
outer=max(radii);inner=min(radii)

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.hide_render=False;ob.select_set(True);bpy.context.view_layer.objects.active=ob

def strip_old_adapter(ob,slots):
    mesh=ob.data
    # Retain source corner normals through removal of the disconnected old mount.
    def key(points):return tuple(sorted(tuple(round(x,9) for x in p) for p in points))
    saved={key(mesh.vertices[i].co for i in f.vertices):{tuple(round(x,9) for x in mesh.vertices[mesh.loops[l].vertex_index].co):tuple(mesh.corner_normals[l].vector) for l in f.loop_indices} for f in mesh.polygons if f.material_index not in slots}
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in slots],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(mesh);bm.free();mesh.update()
    normals=[(0,0,0)]*len(mesh.loops)
    for f in mesh.polygons:
        face=saved[key(mesh.vertices[i].co for i in f.vertices)]
        for l in f.loop_indices:normals[l]=face[tuple(round(x,9) for x in mesh.vertices[mesh.loops[l].vertex_index].co)]
    mesh.normals_split_custom_set(normals)

def physical_uv(ob,index):
    while len(ob.data.uv_layers)<=index:ob.data.uv_layers.new(name='G18Coating'+str(len(ob.data.uv_layers)))
    uv=ob.data.uv_layers[index]
    for f in ob.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(f.normal[a]))]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.1+.5,p[axes[1]]/.1+.5)

def make_adapter(profile,offset,mat):
    count=96
    verts=[Vector((r*math.cos(i*2*math.pi/count),y,r*math.sin(i*2*math.pi/count)))+offset for y,r in profile for i in range(count)]
    faces=[(j*count+i,j*count+(i+1)%count,((j+1)%len(profile))*count+(i+1)%count,((j+1)%len(profile))*count+i) for j in range(len(profile)) for i in range(count)]
    mesh=bpy.data.meshes.new('G18_MeasuredBoreAdapter');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle(0)<.6
    bm.to_mesh(mesh);bm.free()
    part=bpy.data.objects.new('G18_MeasuredBoreAdapter',mesh);bpy.context.collection.objects.link(part);mesh.materials.append(mat)
    for channel in range(3):physical_uv(part,channel)
    select(part);mod=part.modifiers.new('Adapter edge chamfer','BEVEL');mod.width=.00010;mod.segments=2;mod.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=mod.name)
    return part

for kind in ('suppressor','tactical_suppressor','brake'):
    bpy.ops.wm.open_mainfile(filepath=source[kind]['source'])
    ob=bpy.data.objects['SM_M4_titanium_brake' if kind=='titanium_brake' else 'SM_G18_'+kind]
    select(ob)
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    ob.parent=None;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    ob.name='SM_G18_'+kind
    if kind!='titanium_brake':
        strip_old_adapter(ob,{i for i,m in enumerate(ob.data.materials) if 'AdapterSteel' in m.name or m.name=='TacticalMount'})
    else:
        # Pistol-length variant: preserve ports and independently retain the open
        # central passage, following the existing M1911 compact-brake method.
        mesh=ob.data;old=[v.co.copy() for v in mesh.vertices];normals=[n.vector.copy() for n in mesh.corner_normals]
        sy=.043/.0745
        for v,p in zip(mesh.vertices,old):
            radius=math.hypot(p.x,p.z);new_r=radius*(.0065/.006) if radius<=.006 else .0065+(radius-.006)*(.0124-.0065)/(.0182-.006)
            scale=new_r/radius if radius>1e-8 else 1.
            v.co=Vector((p.x*scale,(p.y+.002)*sy+.006,p.z*scale))
        for li,loop in enumerate(mesh.loops):
            p=old[loop.vertex_index];r=math.hypot(p.x,p.z);n=normals[li]
            if r>1e-8:
                radial=Vector((p.x/r,0,p.z/r));s=(.0065/.006) if r<=.006 else (.0065+(r-.006)*(.0124-.0065)/(.0182-.006))/r
                slope=(.0065/.006) if r<=.006 else (.0124-.0065)/(.0182-.006)
                nr=radial*n.dot(radial);axial=Vector((0,n.y,0));n=nr/slope+(n-nr-axial)/s+axial/sy
            else:n.y/=sy
            normals[li]=n.normalized()
        mesh.update();mesh.normals_split_custom_set(normals)
        physical_uv(ob,2)
    if kind!='titanium_brake':
        for v in ob.data.vertices:v.co.y+=.012
    # Keep the established component contract, so geometry aligns in single,
    # dual, preview and dropped copies through the same attachment function.
    extension=.012 if 'suppressor' in kind else .006
    offset=Vector((marker.x-center.x,marker.y-center.y-extension+.00012535,center.z-marker.z))
    body_points=[v.co.copy() for v in ob.data.vertices];rear=min(p.y for p in body_points)
    rear_ring=[p for p in body_points if p.y<rear+.00045]
    join_radius=max(math.hypot(p.x,p.z) for p in rear_ring)-.00015
    join_y=rear+.0008
    # A narrow barrel-sized rear annulus opens smoothly into each donor body.
    # The wall is real annular geometry; no solid cap obstructs the bore.
    profile=[(-.00018,outer+.00012),(.00045,outer+.00015),(.0016,max(outer+.0003,.0072)),
             (max(.0022,rear-.0010),max(outer+.0004,join_radius-.0005)),(join_y,join_radius),
             (join_y,.0065),(.0016,.0065),(-.00018,inner+.00004)]
    for v in ob.data.vertices:v.co+=offset
    adapter_mat=bpy.data.materials.new('M_G18_MuzzleAdapter');adapter=make_adapter(profile,offset,adapter_mat)
    # Match layer names before joining so source structural and coating UVs survive.
    for i,layer in enumerate(adapter.data.uv_layers):
        if i<len(ob.data.uv_layers):layer.name=ob.data.uv_layers[i].name
    select(ob);adapter.select_set(True);bpy.ops.object.join()
    # Remove now-unused donor mounting slots, preserving the slot identities with faces.
    used={p.material_index for p in ob.data.polygons}
    for i in range(len(ob.data.materials)-1,-1,-1):
        if i not in used:ob.data.materials.pop(index=i)
    tip=max(p.y for p in body_points);sockets={'MountForward':Vector((0,.03,0))+offset,'MountUp':Vector((0,0,.03))+offset,'Muzzle':Vector((0,tip,0))+offset}
    for name,point in sockets.items():
        socket=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(socket);socket.parent=ob;socket.location=point;socket.select_set(True)
    ob.data.calc_loop_triangles()
    icons[kind]={'vertices':[list(v.co) for v in ob.data.vertices],'triangles':[list(t.vertices) for t in ob.data.loop_triangles]}
    file=X/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(ob.name+'_Editable.blend')))
    record[kind]={'fbx':str(file),'source':source[kind]['source'],'component_extension_m':extension,'barrel_front_center_root_m':list(center),'source_marker_root_m':list(marker),'measured_outer_radius_m':outer,'measured_inner_radius_m':inner,'component_geometry_offset_m':list(offset),'body_tip_from_barrel_m':tip,'adapter_profile_m':profile,'sockets_blender_m':{n:list(v) for n,v in sockets.items()},'slots':[m.name for m in ob.data.materials],'source_asset':'/Game/Weapons/M4MuzzlesV1/SM_M4_titanium_brake' if kind=='titanium_brake' else '/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_'+kind}
    print('G18_MUZZLE_AUTHORED '+kind,flush=True)
(O/'authoring.json').write_text(json.dumps(record,indent=2))
(O/'icon_geometry.json').write_text(json.dumps(icons,separators=(',',':')))
