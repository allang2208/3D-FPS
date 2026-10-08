"""Replace all V18 fabric/strap geometry with a continuous open mantle and cuffs.

Witch Drape04/06/Seams07 construction: one support for a hanging sheet, regular
proxy, welded sleeve seam, a turned edge rather than duplicate solidified shells.
UE simulation/capture remains the existing UWitchRebuiltClothingAsset pipeline.
"""
from pathlib import Path
import bpy, bmesh, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'GarmentRebuildV19';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GarmentDrapeV18/BoundCongregate_GarmentDrapeV18.blend'))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
if rig.animation_data:rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis.identity()
rig.data.pose_position='REST'
body=bpy.data.objects['BC_Flesh'];body.data.calc_loop_triangles()
P=np.array([v.co[:] for v in body.data.vertices])
T=[tuple(t.vertices) for t in body.data.loop_triangles]
bone_names=[b.name for b in rig.data.bones];bi={n:i for i,n in enumerate(bone_names)}
W=np.zeros((len(P),len(bone_names)))
for v in body.data.vertices:
    for g in v.groups:
        name=body.vertex_groups[g.group].name
        if name in bi:W[v.index,bi[name]]=g.weight
materials={m.name:m for m in bpy.data.materials}
preserved={'BC_Flesh','BC_M_Tag','BC_M_Stamp'}
# Actual deletion in the new authoring scene, not a second cloth layer over V18.
removed=[]
for ob in list(scene.objects):
    if ob.type=='MESH' and ob.name not in preserved:
        removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
report=dict(revision='GarmentRebuildV19',removed_meshes=removed,garments={},
    reuse=['Witch Drape04 single-support sheet','Witch Drape06 regular proxy',
           'Witch Seams07 turned hems','UWitchRebuiltClothingAsset stable capture'],
    unchanged=['flesh vertices/UV/skin','skeleton and transforms','animations','live material assets'],
    rendered=False,gameplay_tested=False)

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def envelope(values,passes=10,wrap=False):
    # Smooth outer envelope over small pustules; never shrink into skin valleys.
    pad=np.pad(values,((1,1),(0,0)),mode='edge')
    broad=np.maximum.reduce([values,pad[:-2],pad[2:]])
    for _ in range(passes):
        v=np.pad(broad,((1,1),(0,0)),mode='edge')
        h=np.pad(broad,((0,0),(1,1)),mode='wrap' if wrap else 'edge')
        broad=np.maximum(values,.4*broad+.15*(v[:-2]+v[2:]+h[:,:-2]+h[:,2:]))
    return broad

def skin(ob,fields):
    for n in bone_names:ob.vertex_groups.new(name=n)
    for i,w in enumerate(fields):
        ids=np.argsort(w)[-4:];total=w[ids].sum()
        for j in ids:
            if w[j]>1e-7:ob.vertex_groups[int(j)].add([i],float(w[j]/total),'REPLACE')
    ob.parent=rig;ob.matrix_parent_inverse=rig.matrix_world.inverted()
    arm=ob.modifiers.new('Original monster rig','ARMATURE');arm.object=rig

def surface(name,points,faces,uvs,fields,material,travel=None,drive=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points.tolist(),[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
    mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='UVMap')
    for f in mesh.polygons:
        f.use_smooth=True
        for li in f.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    color=mesh.color_attributes.new(name='ClothTravel',type='FLOAT_COLOR',domain='POINT')
    edges={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            e=tuple(sorted((a,b)));edges[e]=edges.get(e,0)+1
    boundary={i for e,n in edges.items() if n==1 for i in e}
    for i,p in enumerate(points):
        color.data[i].color=(float(travel[i]/.45) if travel is not None else 0.,
            .12 if i in boundary else .85,float(1-smooth(.55,1.1,p[2])),
            float(drive[i]) if drive is not None else 1.)
    mesh.color_attributes.active_color=color
    mesh.color_attributes.render_color_index=0
    skin(ob,fields)
    return ob

def pair(name,mat,points,faces,uvs,fields,travel,drive,outward,wrap=False):
    proxy=surface(name+'_SimulationProxy',points,faces,uvs,fields,
        bpy.data.materials.get(mat+'_Proxy') or bpy.data.materials.new(mat+'_Proxy'),travel,drive)
    # Orient all faces consistently before capture. No clipped aperture islands.
    bm=bmesh.new();bm.from_mesh(proxy.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    if sum(f.normal.dot(Vector(np.mean([outward[vert.index] for vert in f.verts],axis=0)))*f.calc_area() for f in bm.faces)<0:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(proxy.data);bm.free()
    if wrap:
        uv=proxy.data.uv_layers.active
        for f in proxy.data.polygons:
            values=[uv.data[i].uv.x for i in f.loop_indices]
            if max(values)-min(values)>.5:
                for i in f.loop_indices:
                    if uv.data[i].uv.x<.5:uv.data[i].uv.x+=1
    visible=proxy.copy();visible.data=proxy.data.copy();visible.name=name
    scene.collection.objects.link(visible)
    visible.data.materials.clear();visible.data.materials.append(materials[mat])
    bpy.ops.object.select_all(action='DESELECT');visible.select_set(True)
    bpy.context.view_layer.objects.active=visible
    detail=visible.modifiers.new('Display refinement only','SUBSURF')
    detail.subdivision_type='SIMPLE';detail.levels=1
    # Apply before armature evaluation; the armature is in REST for export.
    bpy.ops.object.modifier_apply(modifier=detail.name)
    # Turn just the free border inward. No Solidify on the entire sheet, no
    # double shell, no side walls along UV seams. The material is two sided.
    bm=bmesh.new();bm.from_mesh(visible.data)
    hem=[e for e in bm.edges if e.is_boundary and
         min(v.co.z for v in e.verts)<float(points[:,2].max())-.12]
    extruded=bmesh.ops.extrude_edge_only(bm,edges=hem)
    for v in extruded['geom']:
        if isinstance(v,bmesh.types.BMVert):v.co+=Vector((0,0,.0035))-v.normal*.002
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(visible.data);bm.free()
    for f in visible.data.polygons:f.use_smooth=True
    proxy.hide_render=True
    report['garments'][name]=dict(proxy_vertices=len(proxy.data.vertices),render_vertices=len(visible.data.vertices),
        max_travel_cm=float(max(travel)*100),skin=[n for i,n in enumerate(bone_names) if fields[:,i].max()>.001],
        construction='continuous sheet, same render/proxy surface, turned free border, no full solidify')
    return proxy

# One continuous asymmetric mantle; deliberate high cut over lateral leg roots,
# longer back hem between the rear legs. The entire right whip shoulder is open.
cols,rows=44,24
v,u=np.mgrid[0:rows+1,0:cols+1].astype(float);u/=cols;v/=rows
phi=np.deg2rad(-106+132*u)
top=1.52+.075*np.sin(u[0]*math.pi)+.015*np.sin(u[0]*math.tau)
hem=.61+.53*smooth(.13,1.22,np.abs(phi[0]))+.018*np.sin(u[0]*math.tau*3+.4)
z=top[None,:]*(1-v)+hem[None,:]*v
origin=np.stack((np.zeros_like(z),np.full_like(z,.16),z),axis=-1)
direction=np.stack((np.sin(phi),np.cos(phi),np.zeros_like(phi)),axis=-1)
# Geometric body envelope, not a body-weight threshold: fused shoulder flesh may
# be influenced by a donor root and must still remain inside the clothing.
flesh_faces=[tuple(t.vertices) for t in body.data.loop_triangles
             if body.data.materials[body.data.polygons[t.polygon_index].material_index].name=='BC_Flesh']
tree=BVHTree.FromPolygons(P.tolist(),flesh_faces,all_triangles=True)
radius=np.empty_like(z)
for row in range(rows+1):
    for col in range(cols+1):
        o,d=Vector(origin[row,col]),Vector(direction[row,col])
        q,_,_,_=tree.ray_cast(o+d*1.65,-d,1.65)
        radius[row,col]=max(.28,(q-o).dot(d)) if q is not None else (.65 if row<5 else .95)
radius=envelope(radius+.043,18)
# Extend below the side/back tangent under gravity, rather than curling the hem
# underneath the belly. The skirt has slack while the top seam stays close.
for row in range(1,rows+1):
    radius[row]=np.maximum(radius[row],radius[row-1]-.008)
fold=(.010+.012*v)*np.sin(u*math.tau*5+.35*v)*smooth(.10,.55,v)
radius+=fold+.016
points=(origin+direction*radius[...,None]).reshape(-1,3)
fields=np.zeros((len(points),len(bone_names)))
# Witch's one waist support applied to the creature's rear torso. All hanging
# fabric shares this support; independent feet/whip bones never pull its hem.
fields[:,bi['body']]=.35;fields[:,bi['body_rear']]=.65
faces=[]
for row in range(rows):
    for col in range(cols):
        i=row*(cols+1)+col;faces.append((i,i+1,i+cols+2,i+cols+1))
travel=.12*smooth(.22,1.,v.ravel())
drive=1.-smooth(.12,.9,v.ravel())
uvs=np.column_stack((u.ravel()*2.5,v.ravel()*1.4))
mantle=pair('BC_MantleV19','BC_RagFabric',points,faces,uvs,fields,travel,drive,direction.reshape(-1,3))

# A leather shoulder yoke lies on the fixed mantle band. Rebuild it instead of
# retaining a strap that spans unrelated openings in the old clothing.
strap_rows=(2,4);sp=np.concatenate([points.reshape(rows+1,cols+1,3)[i] for i in strap_rows])
sd=np.concatenate([direction[i] for i in strap_rows]);sp+=sd*.007
sf=[(i,i+1,i+cols+2,i+cols+1) for i in range(cols)]
sw=np.tile(fields[0],(len(sp),1))
su=np.array([(i/cols*2.5,r*.08) for r in range(2) for i in range(cols+1)])
strap=surface('BC_ShoulderYokeV19',sp,sf,su,sw,materials['BC_Binding'])
# Badge remains on the fixed leather support and shares its complete transform.
tag=bpy.data.objects['BC_M_Tag'];stamp=bpy.data.objects['BC_M_Stamp']
oldcenter=sum((vert.co for vert in tag.data.vertices),Vector())/len(tag.data.vertices)
column=5;target=Vector((sp[column]+sp[cols+1+column])*.5)+Vector(sd[column])*.012
rot=Vector((-1,0,0)).rotation_difference(Vector(sd[column]))
for ob in (tag,stamp):
    for vert in ob.data.vertices:vert.co=target+rot@(vert.co-oldcenter)
    ob.vertex_groups.clear()
    for n,w in (('body',.35),('body_rear',.65)):
        group=ob.vertex_groups.new(name=n);group.add(list(range(len(ob.data.vertices))),w,'REPLACE')

def cuff(name,stem,mat):
    bone=rig.data.bones[stem+'lower'];a,b=np.array(bone.head_local),np.array(bone.tail_local)
    axis=(b-a)/np.linalg.norm(b-a);x=np.cross(axis,(0,0,1));x/=np.linalg.norm(x);y=np.cross(axis,x)
    allowed=[stem+'upper',stem+'lower']
    family=[bi[n] for n in bone_names if n.startswith(stem)]
    faces_skin=[t for t in T if W[list(t)][:,family].sum(axis=1).mean()>.60]
    local_tree=BVHTree.FromPolygons(P.tolist(),faces_skin,all_triangles=True)
    nx,ny=28,12
    vv,uu=np.mgrid[0:ny+1,0:nx].astype(float);uu/=nx;vv/=ny
    along=.34+.31*vv
    centers=a+(b-a)*along[...,None]
    directions=np.cos(uu*math.tau)[...,None]*x+np.sin(uu*math.tau)[...,None]*y
    radii=np.empty_like(uu)
    for r in range(ny+1):
        for c in range(nx):
            o,d=Vector(centers[r,c]),Vector(directions[r,c])
            q,_,_,_=local_tree.ray_cast(o+d*.6,-d,.6)
            radii[r,c]=max(.04,(q-o).dot(d)) if q is not None else .12
    radii=envelope(radii+.026,12,True)
    radii+=.008+.006*np.cos(uu*math.tau*4)*smooth(.1,.8,vv)
    pp=(centers+directions*radii[...,None]).reshape(-1,3)
    ww=np.zeros((len(pp),len(bone_names)))
    # Anatomical surface transfer restricted to this sleeve's own arm chain.
    # Unlike a rigid guessed cylinder, the support follows the actual limb skin.
    for i,p in enumerate(pp):
        q,_,face,_=local_tree.find_nearest(Vector(p));ids=faces_skin[face]
        bary=np.clip(np.array(barycentric_transform(q,*[Vector(P[j]) for j in ids],
            Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0,1)
        field=(bary/max(1e-8,bary.sum()))@W[list(ids)]
        for n in allowed:ww[i,bi[n]]=field[bi[n]]
        if ww[i].sum()<1e-6:ww[i,bi[stem+'lower']]=1
        ww[i]/=ww[i].sum()
    ff=[]
    for r in range(ny):
        for c in range(nx):
            k=(c+1)%nx;ff.append((r*nx+c,r*nx+k,(r+1)*nx+k,(r+1)*nx+c))
    return pair(name,mat,pp,ff,np.column_stack((uu.ravel(),vv.ravel()*.45)),ww,
        .018*smooth(.70,1,vv.ravel()),1.-smooth(.65,1,vv.ravel()),directions.reshape(-1,3),True)

cuff('BC_LeftCuffV19','leg_L2_','BC_SleeveLeft')
cuff('BC_RightCuffV19','leg_R4_','BC_SleeveRight')
rig.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_GarmentRebuildV19.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_GarmentRebuildV19.fbx'),
    use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
    use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP',
    colors_type='SRGB',prioritize_active_color=True)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GARMENT_REBUILD_V19_EXPORTED '+json.dumps(report),flush=True)
