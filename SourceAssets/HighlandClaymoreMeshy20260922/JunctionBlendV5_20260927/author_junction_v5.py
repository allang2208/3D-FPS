"""Author a continuous Highland shoulder before splitting interchangeable parts.

The entire gemstone belongs to the guard. The new shared seat is above it.
Old hidden V-cut fans are removed by their authored UV marker, not by assuming
their fan centres lie on either cut plane. No renders or acceptance tests.
"""
import json
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parent
BASE = P.parent
OUT = P/'Export'
OUT.mkdir(exist_ok=True)
CUT_Z = .058
CUT_SLOPE = .95
blades = ['SM_Highland_Blade_'+n for n in ['factory','extended_edge','heavy_spine','feather_edge']]
guards = ['SM_Highland_Guard_'+n for n in ['factory','bastion_guard','riposte_guard','light_guard']]


def smooth(t):
    t = np.clip(t,0.,1.)
    return t*t*(3-2*t)


def coordinates(mesh):
    return np.array([v.co[:] for v in mesh.vertices],dtype=np.float64)


def profile(mesh):
    points = coordinates(mesh)
    edges = np.array([e.vertices[:] for e in mesh.edges])
    a,b = points[edges[:,0]],points[edges[:,1]]
    tip = float(points[:,2].max())
    stations = np.linspace(.105,tip-.00001,600)
    left,right = [],[]
    for z in stations:
        hit = (np.minimum(a[:,2],b[:,2]) <= z)&(np.maximum(a[:,2],b[:,2]) > z)
        aa,bb = a[hit],b[hit]
        xx = aa[:,0]+(bb[:,0]-aa[:,0])*(z-aa[:,2])/(bb[:,2]-aa[:,2])
        left.append(max(.00001,-float(xx.min())))
        right.append(max(.00001,float(xx.max())))
    return tip,stations,np.array(left),np.array(right)


def seed_normals(mesh):
    values = np.array([n.vector[:] for n in mesh.corner_normals],dtype=np.float32)
    attr = mesh.attributes.get('AuthorNormal') or mesh.attributes.new('AuthorNormal','FLOAT_VECTOR','CORNER')
    attr.data.foreach_set('vector',values.ravel())


def master(blade,guard):
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for source in [blade,guard]:
        obj = source.copy(); obj.data = source.data.copy()
        bpy.context.scene.collection.objects.link(obj)
        seed_normals(obj.data)
        for slot in obj.material_slots:
            if slot.material and slot.material.name.startswith('M_HighlandClaymoreSurface'):
                slot.material = bpy.data.materials['M_HighlandClaymoreSurface']
        obj.hide_set(False);obj.select_set(True);copies.append(obj)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = 'Continuous_'+blade.name+'_'+guard.name
    mesh = obj.data
    bm = bmesh.new();bm.from_mesh(mesh)
    uv = bm.loops.layers.uv[0]
    # The old fan centre is above the V's lowest point. Testing all vertex
    # positions against the V misses those caps and leaves crossing roof faces.
    old_caps = [face for face in bm.faces
                if all(v.co.z > .0001 for v in face.verts)
                and all((loop[uv].uv-Vector((.02,.02))).length < .000002 for loop in face.loops)]
    removed = len(old_caps)
    bmesh.ops.delete(bm,geom=old_caps,context='FACES')
    boundary = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)
                and abs(v.co.z-.005-.95*abs(v.co.x)) < .000004]
    bmesh.ops.remove_doubles(bm,verts=boundary,dist=.0000005)
    bm.to_mesh(mesh);bm.free();mesh.update()
    points = coordinates(mesh)
    tip,stations,left,right = profile(blade.data)
    x,y,z = points.T
    width = np.where(x < 0,np.interp(z,stations,left),np.interp(z,stations,right))
    t = smooth((z-.09)/.04)
    width = .032*(1-t)+width*t
    grind = smooth((np.abs(x)/np.maximum(width,.00004)-.70)/.30)
    # Ease the cutting bevel into a full supported shoulder instead of carving
    # the V4 thickness trough at x=32 mm into the wing roots.
    shoulder_to_blade = smooth((z-.014)/.076)
    half = .006-.00575*grind*shoulder_to_blade
    half *= 1-.97*smooth((z-(tip-.022))/.022)
    dz = z+.001589306
    diamond = np.abs(x+.00020)/.0132+np.where(dz >= 0,dz/.0202,-dz/.0167)
    half += .0015*(1-smooth((diamond-1.02)/.22))+.0065*np.clip(1-diamond,0,1)
    weight = (1-smooth((np.abs(x)-.038)/.030))*smooth((z+.047)/.015)
    weight = np.where(z >= .105,1-smooth((np.abs(x)-.075)/.015),weight)
    result = points.copy()
    result[:,1] = y+weight*(np.tanh(y/.00018)*half-y)
    original_normals = np.array([v.vector[:] for v in mesh.attributes['AuthorNormal'].data])
    mesh.vertices.foreach_set('co',result.astype(np.float32).ravel());mesh.update()
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    poly_ids = np.array([t.polygon_index for t in mesh.loop_triangles])
    points = result[triangles]
    cross = np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
    normals = cross/np.maximum(np.linalg.norm(cross,axis=1)[:,None],1e-14)
    bottom = np.all(np.abs(points[:,:,2]+.05) < .000003,axis=1)
    acc = np.zeros_like(result)
    for i in range(3):
        a,b = points[:,(i+1)%3]-points[:,i],points[:,(i+2)%3]-points[:,i]
        a /= np.maximum(np.linalg.norm(a,axis=1)[:,None],1e-14)
        b /= np.maximum(np.linalg.norm(b,axis=1)[:,None],1e-14)
        angle = np.arccos(np.clip(np.sum(a*b,axis=1),-1,1));angle[bottom] = 0
        np.add.at(acc,triangles[:,i],normals*angle[:,None])
    acc /= np.maximum(np.linalg.norm(acc,axis=1)[:,None],1e-14)
    loop_ids = np.array([loop.vertex_index for loop in mesh.loops])
    blend = smooth(weight[loop_ids])[:,None]
    normals = original_normals*(1-blend)+acc[loop_ids]*blend
    cap_polys = set(poly_ids[bottom].tolist())
    for face in mesh.polygons:
        if face.index in cap_polys:normals[list(face.loop_indices)] = face.normal[:]
        face.use_smooth = True
    normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-14)
    mesh.update();mesh.normals_split_custom_set(normals.tolist())
    mesh.attributes['AuthorNormal'].data.foreach_set('vector',normals.astype(np.float32).ravel())
    obj['old_v_cut_cap_faces_removed'] = removed
    obj['new_cut_z_m'] = CUT_Z
    return obj


def clip(polygon,fn,inside=True):
    out = []
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        da,db = fn(a[0])*(1 if inside else -1),fn(b[0])*(1 if inside else -1)
        if da >= 0:out.append(a)
        if (da >= 0)!=(db >= 0):
            t = da/(da-db)
            out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out


def split(source,source_name,kind):
    mesh = source.data;mesh.calc_loop_triangles()
    A = lambda p:p.z-CUT_Z-CUT_SLOPE*p.x
    B = lambda p:p.z-CUT_Z+CUT_SLOPE*p.x
    normals = [n.vector.copy() for n in mesh.corner_normals]
    uv_layers = list(mesh.uv_layers)
    color_layers = list(mesh.color_attributes)
    verts,faces,corners,mats = [],[],[],[]
    for tri in mesh.loop_triangles:
        poly = []
        for li in tri.loops:
            vi = mesh.loops[li].vertex_index
            entry = [mesh.vertices[vi].co.copy(),normals[li]]
            entry.extend(layer.data[li].uv.copy() for layer in uv_layers)
            entry.extend(Vector(layer.data[li if layer.domain=='CORNER' else vi].color) for layer in color_layers)
            poly.append(tuple(entry))
        groups = [clip(clip(poly,A),B)] if kind=='blade' else [clip(poly,A,False),clip(clip(poly,A),B,False)]
        for polygon in groups:
            for i in range(1,len(polygon)-1):
                tri_points = [polygon[0],polygon[i],polygon[i+1]]
                if (tri_points[1][0]-tri_points[0][0]).cross(tri_points[2][0]-tri_points[0][0]).length < 1e-12:continue
                faces.append(tuple(range(len(verts),len(verts)+3)))
                verts.extend(p[0] for p in tri_points);corners.extend(tri_points);mats.append(tri.material_index)
    name = source_name+'_JunctionV5'
    data = bpy.data.meshes.new(name);data.from_pydata(verts,[],faces)
    for mat in mesh.materials:data.materials.append(mat)
    data.update()
    normal = data.attributes.new('SurfaceNormal','FLOAT_VECTOR','CORNER')
    dest_uv = [data.uv_layers.new(name=layer.name) for layer in uv_layers]
    dest_color = [data.color_attributes.new(name=layer.name,type='FLOAT_COLOR',domain='CORNER') for layer in color_layers]
    for face,material in zip(data.polygons,mats):
        face.material_index = material;face.use_smooth = True
        for li in face.loop_indices:
            point = corners[data.loops[li].vertex_index]
            normal.data[li].vector = point[1].normalized()
            for index,layer in enumerate(dest_uv):layer.data[li].uv = point[2+index]
            for index,layer in enumerate(dest_color):layer.data[li].color = point[2+len(dest_uv)+index]
    bm = bmesh.new();bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000003)
    edges = [e for e in bm.edges if e.is_boundary and
             any(all(abs(fn(v.co))<.000004 for v in e.verts) for fn in [A,B])]
    if edges:
        # Centre lies on the actual V apex. A mean-height fan creates an
        # artificial raised roof crossing the gemstone on the old interface.
        center = bm.verts.new((0,0,CUT_Z))
        nl = bm.loops.layers.float_vector['SurfaceNormal']
        for edge in edges:
            loop = edge.link_loops[0]
            a,b = loop.vert,loop.link_loop_next.vert
            face = bm.faces.new((b,a,center));face.smooth=False;face.material_index=0;face.normal_update()
            for corner in face.loops:
                corner[nl] = face.normal
                for uv in bm.loops.layers.uv.values():corner[uv].uv=(.02,.02)
    bm.to_mesh(data);bm.free();data.update()
    saved_normals = [v.vector[: ] for v in data.attributes['SurfaceNormal'].data]
    # Set smooth first: assigning it after custom normals can discard the data.
    for face in data.polygons:face.use_smooth=True
    data.update();data.normals_split_custom_set(saved_normals)
    obj = bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    obj['revision'] = 'V5: gem owned by guard; continuous welded shoulder authored before split'
    obj['source_mesh'] = source_name
    obj['new_interface_cut'] = 'z=.058+.95*abs(x) metres'
    obj['old_v_cut_cap_faces_removed'] = source['old_v_cut_cap_faces_removed']
    return obj


def export(obj,source_name,kind):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    print('JUNCTION_V5_EXPORTED '+obj.name,flush=True)
    return {'source_mesh':source_name,'mesh':obj.name,'fbx':str(path),'kind':kind}


bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Integration/HighlandClaymore_Modular_Editable.blend'))
for file,name in [('BroadbladeThicknessV2_20260922/Highland_Broadblade_ThickV2_Editable.blend','SM_Highland_Blade_Broadblade_ThickV2'),
                  ('ClovenGuard20260922/Highland_ClovenGuard_Editable.blend','SM_Highland_Guard_Cloven')]:
    with bpy.data.libraries.load(str(BASE/file),link=False) as (available,selected):selected.objects=[name]
    bpy.context.scene.collection.objects.link(selected.objects[0])
blades.append('SM_Highland_Blade_Broadblade_ThickV2');guards.append('SM_Highland_Guard_Cloven')
source_blade=bpy.data.objects[blades[0]];source_guard=bpy.data.objects[guards[0]]
reports=[];made={}
for name in blades:
    joined=master(bpy.data.objects[name],source_guard)
    obj=split(joined,name,'blade');made[name]=obj;reports.append(export(obj,name,'blade'))
    if name==blades[0]:
        obj=split(joined,guards[0],'guard');made[guards[0]]=obj;reports.append(export(obj,guards[0],'guard'))
        joined.name='Highland_ContinuousJunction_MasterV5';joined.hide_set(True);joined.hide_render=True
    else:bpy.data.objects.remove(joined,do_unlink=True)
for name in guards[1:]:
    joined=master(source_blade,bpy.data.objects[name])
    obj=split(joined,name,'guard');made[name]=obj;reports.append(export(obj,name,'guard'))
    bpy.data.objects.remove(joined,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
copies=[]
for original in [made[blades[0]],made[guards[0]],bpy.data.objects['SM_Highland_Grip_factory'],bpy.data.objects['SM_Highland_Pommel_factory']]:
    obj=original.copy();obj.data=original.data.copy();bpy.context.scene.collection.objects.link(obj)
    obj.hide_set(False);obj.select_set(True);copies.append(obj)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
world=bpy.context.object;world.name='SM_HighlandClaymore_JunctionV5'
reports.append(export(world,'SM_HighlandClaymore','world'))
visible={made[blades[0]].name,made[guards[0]].name,'SM_Highland_Grip_factory','SM_Highland_Pommel_factory'}
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':obj.hide_set(obj.name not in visible);obj.hide_render=obj.name not in visible
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ContinuousJunctionV5_Editable.blend'))
(P/'author_receipt.json').write_text(json.dumps({'assets':reports,'new_cut_z_m':CUT_Z,'cut_slope':CUT_SLOPE,
    'steel_thickness_mm':12,'gem_peak_above_steel_mm':8,'tested':False},indent=2),encoding='utf-8')
print('JUNCTION_V5_AUTHOR_COMPLETE',flush=True)
