"""Fit thin grip skins to the original stock neck without changing the host or hands."""
import bpy,bmesh,json,math,heapq
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
source=bpy.data.objects['M24_base'];m=source.data
# Source geometry has UV splits. Connected positions identify the stock shell.
parent=list(range(len(m.vertices)));lookup={}
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def join(a,b):parent[root(a)]=root(b)
for v in m.vertices:
    key=tuple(round(x,6) for x in v.co)
    if key in lookup:join(v.index,lookup[key])
    else:lookup[key]=v.index
for e in m.edges:join(*e.vertices)
stock=root(0);faces=[list(p.vertices) for p in m.polygons if root(p.vertices[0])==stock]
mesh=bpy.data.meshes.new('M24 original stock neck');mesh.from_pydata([v.co for v in m.vertices],[],faces);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
# Cuts stay behind the trigger guard and below the moving bolt/receiver.
planes=[((0,-.095,.04),(0,-1,.23)),((0,.041,0),(0,1,0)),((0,0,.097),(0,0,1))]
for point,normal in planes:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
        plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.normal_update();bm.to_mesh(mesh);bm.free()
native=bpy.data.objects.new('M24_OriginalGripSurface',mesh);bpy.context.collection.objects.link(native)
native.data.materials.clear()
factory=bpy.data.materials.new('M24 factory polymer');factory.use_nodes=True
p=next(n for n in factory.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.019,.019,.018,1);p.inputs['Roughness'].default_value=.55
native.data.materials.append(factory)
for p in native.data.polygons:p.use_smooth=True
variants={};records=[]
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
    skin=native.copy();skin.data=native.data.copy();bpy.context.collection.objects.link(skin);skin.name='SM_M24_'+key
    bm=bmesh.new();bm.from_mesh(skin.data)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3,use_grid_fill=True);bm.normal_update()
    # Taper the outline into the stock; maximum offset is only 0.16 mm.
    distance={v:0.0 for v in bm.verts if v.is_boundary};queue=[(0.0,i,v) for i,v in enumerate(distance)];heapq.heapify(queue);serial=len(queue)
    while queue:
        d,_,v=heapq.heappop(queue)
        if d>distance[v]:continue
        for e in v.link_edges:
            other=e.other_vert(v);nd=d+e.calc_length()
            if nd<distance.get(other,1e9):distance[other]=nd;serial+=1;heapq.heappush(queue,(nd,serial,other))
    for v in bm.verts:
        t=min(1,distance.get(v,.004)/.003);t=t*t*(3-2*t)
        v.co+=v.normal*(.000055+.000105*t)
    bm.normal_update();bm.to_mesh(skin.data);bm.free()
    uv=skin.data.uv_layers.new(name='GripPhysicalUV')
    for p in skin.data.polygons:
        coords=[skin.data.vertices[skin.data.loops[i].vertex_index].co for i in p.loop_indices]
        vs=[math.atan2(v.x,v.z-.035)/(2*math.pi) for v in coords]
        if max(vs)-min(vs)>.5:vs=[v+1 if v<0 else v for v in vs]
        for i,v,q in zip(p.loop_indices,coords,vs):uv.data[i].uv=((v.y-.23*v.z)/.08,q*1.7)
        p.use_smooth=True
    mat=bpy.data.materials.new('M24_'+key);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;p=next(n for n in n if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(.012,.013,.013,1) if key=='phantom_reargrip' else ((.016,.016,.015,1) if key=='stable_antislip_reargrip' else (.022,.022,.021,1))
    p.inputs['Roughness'].default_value={'phantom_reargrip':.5,'stable_antislip_reargrip':.67,'balanced_reargrip':.56}[key]
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'Textures'/('T_M24_'+key+'_N.png')));tex.image.colorspace_settings.name='Non-Color'
    nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    skin.data.materials.clear();skin.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT');skin.select_set(True);bpy.context.view_layer.objects.active=skin
    path=O/'Exports'/(skin.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,use_mesh_modifiers=False)
    variants[key]=skin;skin.hide_render=True;skin.hide_set(True)
    records.append(dict(id=key,file=str(path),vertices=len(skin.data.vertices),faces=len(skin.data.polygons),offset_mm=[.055,.16]))
native.hide_set(True);native.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_RearGrip_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(dict(source=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),
    variants=records,host_geometry_changed=False,hand_animation_changed=False,source_axes='M24 source metres; FBX -Y/Z',
    grip_limits=dict(rear_y_at_z04=-.095,front_y=.041,top_z=.097),max_surface_offset_mm=.16),indent=2))
print('M24_REAR_GRIP_AUTHORED',json.dumps(records),flush=True)
