"""Keep one continuous root surface and isolate only the accidental lip weld."""
from pathlib import Path
import bpy,bmesh,json,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from mathutils.kdtree import KDTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'TentacleWhipV3'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RigRepairV3/BoundCongregate_RigV3.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
body=bpy.data.objects['BC_Flesh'];original=body.data.copy()
partition=np.load(ROOT/'TentacleRepairV2/partition.npz');mask=partition['face_mask'];curve=partition['curve'];curve_s=partition['curve_s']
def contact_fade(z):
    a=max(0.,min(1.,(z+.27)/.04));b=max(0.,min(1.,(-.04-z)/.04))
    return a*a*(3-2*a)*b*b*(3-2*b)
# Give the formerly welded strand a small physical clearance from the lip.
# This changes only that repaired contact strip, not the original free organ.
for p in curve:p[1]-=.014*contact_fade(p[2])
curve_s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curve[:,:3],axis=0),axis=1))]
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text());scale=recipe['scale'];ground=recipe['ground_z']
def world(p):return Vector((p[0]*scale,p[1]*scale,(p[2]-ground)*scale))
def source(p):return np.array((p.x/scale,p.y/scale,p.z/scale+ground))
# FBX/source order is retained from the original GLB through RigV3.
body.data.calc_loop_triangles()
assert len(body.data.polygons)==len(mask)
points=[v.co.copy() for v in original.vertices];faces=[p.vertices[:] for p in original.polygons]
bvh=BVHTree.FromPolygons(points,faces)
old_uv=original.uv_layers.active
original_normals=[n.vector.copy() for n in original.corner_normals]
chain_names=[g.name for g in body.vertex_groups if g.name.startswith(('curl_','feeler_'))]
old_names=[g.name for g in body.vertex_groups]
rest_ids=[i for i,n in enumerate(old_names) if n not in chain_names]
weights=np.zeros((len(points),len(old_names)),np.float32)
for v in body.data.vertices:
    for g in v.groups:weights[v.index,g.group]=g.weight
weights[:,[old_names.index(n) for n in chain_names]]=0
usable=weights.sum(1)>.02
# Fill only completely contaminated flesh from the nearest valid flesh sample.
# All existing non-tentacle influences and donor-limb assignments remain.
kd=KDTree(int(usable.sum()))
for i in np.where(usable)[0]:kd.insert(points[int(i)],int(i))
kd.balance()
for i in np.where(~usable)[0]:weights[i]=weights[kd.find(points[int(i)])[1]]
weights/=weights.sum(1)[:,None]
for n in chain_names:
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob.vertex_groups.get(n):ob.vertex_groups.remove(ob.vertex_groups[n])
def nearest_weights(p):
    hit,normal,index,dist=bvh.find_nearest(p);face=original.polygons[index];ids=list(face.vertices[:3])
    bc=barycentric_transform(hit,*[points[i] for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    bc=np.maximum(np.array(bc),0);bc/=max(1e-8,bc.sum())
    w=bc@weights[ids];order=np.argsort(w)[-8:];values=w[order];values/=values.sum()
    return [(old_names[int(i)],float(a)) for i,a in zip(order,values) if a>1e-6]
def set_weights(ob,vi,values):
    for n,w in values:
        group=ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n);group.add([vi],w,'REPLACE')
# Work separately only while repairing the lip. The actual shoulder boundary
# remains open until both sides are welded back into one continuous surface.
tentacle=body.copy();tentacle.data=body.data.copy();tentacle.name='BC_AttackTentacle'
bpy.context.collection.objects.link(tentacle)
mat=body.data.materials[0].copy();mat.name='BC_AttackTentacle';tentacle.data.materials[0]=mat
report={'revision':'TentacleWhipV3','original_faces':len(mask),'selected_faces':int(mask.sum()),'objects':{}}
for ob,is_tentacle in [(body,False),(tentacle,True)]:
    bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
    # Weld only exact UV duplicates. Per-loop UVs/normals remain on the faces.
    bmesh.ops.delete(bm,geom=[f for i,f in enumerate(bm.faces) if bool(mask[i])!=is_tentacle],context='FACES')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
    root_tag=bm.verts.layers.int.new('BCRootJoin')
    boundary_edges={e for e in bm.edges if e.is_boundary};root_edges=set()
    while boundary_edges:
        seed=boundary_edges.pop();component={seed};pending=[seed]
        while pending:
            edge=pending.pop()
            for v in edge.verts:
                for neighbour in v.link_edges:
                    if neighbour in boundary_edges:
                        boundary_edges.remove(neighbour);component.add(neighbour);pending.append(neighbour)
        verts={v for e in component for v in e.verts}
        center=np.mean([source(v.co) for v in verts],axis=0)
        if center[0]>.20 and abs(center[2]-.220)<.04:
            root_edges.update(component)
            for v in verts:v[root_tag]=1
    if not root_edges:raise RuntimeError('Original shoulder boundary was not found')
    # Mark new patch faces so UV reprojection is limited to actual repairs.
    tag=bm.faces.layers.int.new('BCRepairPatch')
    result=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary and e not in root_edges],sides=0)
    patch_faces=[f for f in result['faces'] if f.is_valid]
    # Blender's automatic fill can skip the long concave lip-contact loop.
    # Fill that closed loop explicitly, then tessellate and subdivide it.
    remaining_edges={e for e in bm.edges if e.is_boundary and e not in root_edges}
    while remaining_edges:
        first=remaining_edges.pop();ring=[first.verts[0],first.verts[1]];walk=first
        while ring[-1]!=ring[0]:
            choices=[e for e in ring[-1].link_edges if e in remaining_edges]
            if len(choices)!=1:break
            walk=choices[0];remaining_edges.remove(walk);ring.append(walk.other_vert(ring[-1]))
        if len(ring)>8 and ring[-1]==ring[0]:
            patch_faces.append(bm.faces.new(ring[:-1]))
    for f in patch_faces:f[tag]=1
    bmesh.ops.triangulate(bm,faces=list(patch_faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    for iteration in range(7):
        long_edges=[e for e in bm.edges if e.calc_length()>.038 and all(f[tag] for f in e.link_faces) and len(e.link_faces)==2]
        if not long_edges:break
        bmesh.ops.subdivide_edges(bm,edges=long_edges,cuts=1,use_grid_fill=True)
    uv=bm.loops.layers.uv.active
    patches=0
    for f in bm.faces:
        if not f[tag]:continue
        patches+=1
        for loop in f.loops:
            hit,normal,index,dist=bvh.find_nearest(loop.vert.co);face=original.polygons[index]
            ids=list(face.vertices[:3]);loops=list(face.loop_indices[:3])
            a,b,c=[Vector((*old_uv.data[j].uv,0)) for j in loops]
            tex=barycentric_transform(hit,*[points[j] for j in ids],a,b,c)
            loop[uv].uv=(tex.x,tex.y)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    remaining=sum(e.is_boundary for e in bm.edges)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    if is_tentacle:
        for v in ob.data.vertices:
            p=source(v.co);fade=contact_fade(p[2])
            if fade<=0:continue
            cx=float(np.interp(p[2],[-.255,-.225,-.18,-.13,-.08,-.055],[-.03961,-.049,-.057,-.055,-.054,-.05485]))
            cy=float(np.interp(p[2],[-.255,-.225,-.18,-.13,-.08,-.055],[-.47016,-.473,-.476,-.477,-.477,-.47553]))
            angle=math.atan2((p[1]-cy)/.020,(p[0]-cx)/.012)
            repaired=np.array([cx+.012*math.cos(angle),cy-.014+.020*math.sin(angle),p[2]])
            v.co=world(p*(1-fade)+repaired*fade)
        ob.data.update()
    report['objects'][ob.name]={'vertices':len(ob.data.vertices),'faces':len(ob.data.polygons),'patch_faces':patches,'boundary_edges':remaining}
    ob.vertex_groups.clear()
    if not is_tentacle:
        for v in ob.data.vertices:
            p=source(v.co)
            join=ob.data.attributes['BCRootJoin'].data[v.index].value
            set_weights(ob,v.index,[('body',1.)] if join or p[0]>.20 and .200<p[2]<.232 else nearest_weights(v.co))

# Keep clothing and its simulation proxies outside every attack-chain weight.
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or ob in (body,tentacle):continue
    for v in ob.data.vertices:
        entries=[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups]
        total=sum(w for n,w in entries)
        if total>.02:
            for n,w in entries:ob.vertex_groups[n].add([v.index],w/total,'REPLACE')
        else:set_weights(ob,v.index,nearest_weights(v.co))

count=57
distances=np.linspace(0,curve_s[-1],count+1)
nodes=np.column_stack([np.interp(distances,curve_s,curve[:,i]) for i in range(3)])
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for i in range(count):
    bone=rig.data.edit_bones.new(f'attack_tentacle_{i:02d}');bone.head=world(nodes[i]);bone.tail=world(nodes[i+1])
    bone.parent=rig.data.edit_bones[f'attack_tentacle_{i-1:02d}'] if i else rig.data.edit_bones['body']
    bone.use_connect=bool(i);bone.align_roll(Vector((0,1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
curve_tree=KDTree(len(curve))
for i,p in enumerate(curve):curve_tree.insert(world(p[:3]),i)
curve_tree.balance()
# Seam remains body-bound on both surfaces; influence releases gradually over
# the first 30 cm of the original appendage. The moving part has zero torso,
# mouth, leg, old curl or old feeler influences.
for v in tentacle.data.vertices:
    p=source(v.co);near=curve_tree.find(v.co)[1];along=float(curve_s[near]);r=float(curve[near,3])
    seam=bool(tentacle.data.attributes['BCRootJoin'].data[v.index].value)
    release=max(0,min(1,(along-.04)/.16));release=release*release*(3-2*release)
    if seam:release=0
    blend=[]
    if release<1:blend.append(('body',1-release))
    position=along/curve_s[-1]*count-.5
    ids=np.arange(max(0,int(math.floor(position))-1),min(count,int(math.floor(position))+3))
    values=np.exp(-((ids-position)/.9)**2);values/=values.sum()
    blend.extend((f'attack_tentacle_{int(i):02d}',float(w)*release) for i,w in zip(ids,values))
    set_weights(tentacle,v.index,blend)

# One connected root: no coincident closing discs, no independent root rings.
# Retain two face materials for semantic selection; both use the flesh shader.
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True);tentacle.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.join()
bm=bmesh.new();bm.from_mesh(body.data)
root_tag=bm.verts.layers.int.get('BCRootJoin')
root_verts=[v for v in bm.verts if v[root_tag]]
before=len(root_verts)
bmesh.ops.remove_doubles(bm,verts=root_verts,dist=.000025)
report['root_join']={'input_vertices':before,'welded_vertices':sum(bool(v[root_tag]) for v in bm.verts),'closing_caps':0}
bm.to_mesh(body.data);bm.free();body.data.update()
# The shared boundary and its imported material duplicates must have exactly
# the same deformation, including at extreme rearward windup.
for v in body.data.vertices:
    if body.data.attributes['BCRootJoin'].data[v.index].value:
        for group in body.vertex_groups:group.remove([v.index])
        set_weights(body,v.index,[('body',1.)])
for ob in (body,):
    for poly in ob.data.polygons:poly.use_smooth=True
    ob.data.update()
    normals=[]
    for loop in ob.data.loops:
        p=ob.data.vertices[loop.vertex_index].co
        hit,normal,index,dist=bvh.find_nearest(p);face=original.polygons[index]
        if dist<.0001:
            ids=list(face.vertices[:3]);loops=list(face.loop_indices[:3])
            n=barycentric_transform(hit,*[points[j] for j in ids],*[original_normals[j] for j in loops]).normalized()
        else:n=ob.data.corner_normals[loop.index].vector
        normals.append(n)
    # Preserve the original continuous outer normals and UVs at the root.
    ob.data.normals_split_custom_set(normals)
bpy.context.view_layer.update()
report.update(bones=count,chain_length_cm=float(curve_s[-1]*scale*100),source_body_geometry_preserved_except_contact_patch=True)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_TentacleV3.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_TentacleV3.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
print('TENTACLE_V3_AUTHORED',json.dumps(report),flush=True)
