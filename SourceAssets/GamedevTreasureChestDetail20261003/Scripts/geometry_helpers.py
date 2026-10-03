"""Refine the gamedev treasure toward the official closed/open references.

Keeps the migrated Root/Lid rig, bind pose, 0.65 source scale, material
identities, UV convention, FBX names and the 1 s opening action. Geometry is
rebuilt as angle-iron framing, paneled walls, relief emblems, a cartouche
escutcheon with lid hasp, a rosette medallion, bail handles and bracket feet.
Background Blender only; no renders or tests.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

HERE=Path(__file__).resolve().parents[1]; OUT=HERE/'Authored'; OUT.mkdir(parents=True,exist_ok=True)
PREVIOUS=HERE.parent/'GamedevTreasureChest20260922/Authored'
bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS/'GamedevTreasureChest_UE.blend'))
scene=bpy.context.scene
arm=bpy.data.objects['GamedevTreasureChestRig']
for obj in list(scene.objects):
    if obj!=arm:bpy.data.objects.remove(obj,do_unlink=True)
arm.animation_data_clear();arm.pose.bones['Lid'].rotation_quaternion=Quaternion()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01;scene.render.fps=30
IRON,GOLD,INNER=range(3)
names=['Treasure_BlackIron','Treasure_AntiqueGold','Treasure_Interior']
materials=[bpy.data.materials[n] for n in names]
parts=[];pieces=[]
mapping=Matrix(((0,-.65,0,0),(.65,0,0,0),(0,0,.65,0),(0,0,0,1)))

def finish(obj,name,mat,bone='Root',bevel=0):
    obj.name=name
    if not obj.data.materials:
        obj.data.materials.append(materials[mat])
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    if bevel:
        mod=obj.modifiers.new('MachinedEdges','BEVEL');mod.width=bevel;mod.segments=3
        mod.affect='EDGES';mod.limit_method='ANGLE';mod.angle_limit=math.radians(35)
        mod.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.update()
    obj.data.transform(mapping @ obj.matrix_world)
    obj.matrix_world=Matrix.Identity(4)
    obj.data.update()
    uv=obj.data.uv_layers.new(name='UV0_Physical') if not obj.data.uv_layers else obj.data.uv_layers[0]
    for face in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        for index in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[index].vertex_index].co/100
            uv.data[index].uv=(p.y,p.z) if axis==0 else (p.x,p.z) if axis==1 else (p.x,p.y)
    group=obj.vertex_groups.new(name=bone);group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    obj.select_set(False);parts.append(obj);pieces.append(dict(name=name,bone=bone))
    return obj

def box(name,loc,size,mat=GOLD,bone='Root',bevel=1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object;obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,mat,bone,bevel)

def cylinder(name,loc,radius,depth,mat=GOLD,bone='Root',axis='Z',bevel=.4):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=loc)
    obj=bpy.context.object
    if axis=='X':obj.rotation_euler.y=math.pi/2
    if axis=='Y':obj.rotation_euler.x=math.pi/2
    for face in obj.data.polygons:face.use_smooth=len(face.vertices)==4
    return finish(obj,name,mat,bone,bevel)

def stud(name,loc,radius,mat=GOLD,bone='Root',squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=7,radius=radius,location=loc)
    obj=bpy.context.object;obj.scale=(1,1,squash)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for face in obj.data.polygons:face.use_smooth=True
    return finish(obj,name,mat,bone)

def raw(name,verts,faces,indices,bone='Root',smooth=True,bevel=0):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces)
    for m in materials:data.materials.append(m)
    for face,mat in zip(data.polygons,indices):face.material_index=mat;face.use_smooth=smooth
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    return finish(obj,name,mat,bone,bevel)

def prism(name,profile,mode,fixed,cu,cv,h,t0=0,mat=GOLD,bone='Root',bevel=0):
    """Extrude a (u,v) profile from a body surface outward: t0 .. t0+h."""
    n=len(profile);verts=[]
    for t in (t0,t0+h):
        for u,v in profile:
            if mode=='front':verts.append((cu+u,fixed-t,cv+v))
            elif mode=='back':verts.append((cu+u,fixed+t,cv+v))
            elif mode=='right':verts.append((fixed+t,cu+u,cv+v))
            elif mode=='left':verts.append((fixed-t,cu+u,cv+v))
            else:verts.append((cu+u,cv+v,fixed+t))
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces+=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return raw(name,verts,faces,[mat]*(n+2),bone,smooth=False,bevel=bevel)

def band_yz(name,profile,mat=GOLD):
    """Prism with a (y,z) profile extruded along x."""
    verts=[(x,y,z) for x in (-99,99) for y,z in profile]
    m=len(profile);faces=[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]
    faces+=[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
    return raw(name,verts,faces,[mat]*(m+2),'Root',smooth=False,bevel=.4)

def band_xz(name,profile,mat=GOLD):
    """Prism with an (x,z) profile extruded along y."""
    verts=[(x,y,z) for y in (-71,71) for x,z in profile]
    m=len(profile);faces=[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]
    faces+=[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
    return raw(name,verts,faces,[mat]*(m+2),'Root',smooth=False,bevel=.4)

def band_xy(name,profile,z0,z1,mat=GOLD,bone='Root',bevel=.4):
    """Prism with an (x,y) profile extruded along z."""
    verts=[(x,y,z) for z in (z0,z1) for x,y in profile]
    m=len(profile);faces=[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]
    faces+=[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
    return raw(name,verts,faces,[mat]*(m+2),bone,smooth=False,bevel=bevel)

def curve(name,points,radius=1.25,mat=GOLD,bone='Root',cap_studs=True):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D'
    data.resolution_u=12;data.bevel_depth=radius;data.bevel_resolution=3;data.use_fill_caps=True
    spline=data.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    mesh_obj=bpy.context.object
    # Headless convert ignores fill caps; weld each boundary ring closed.
    data2=mesh_obj.data;bm=bmesh.new();bm.from_mesh(data2)
    rest=[e for e in bm.edges if e.is_boundary]
    while rest:
        loop=[rest.pop()];grow=True
        while grow:
            grow=False
            for e in rest[:]:
                if any(v in loop[0].verts or v in loop[-1].verts for v in e.verts):
                    loop.append(e);rest.remove(e);grow=True
        try:
            ring=[];cur=loop[0].verts[0];prev=None
            for _ in range(len(loop)):
                nxt=next(ed for ed in cur.link_edges if ed.is_boundary and ed is not prev)
                ring.append(cur);prev=nxt;cur=nxt.other_vert(cur)
            bm.faces.new(ring)
        except (StopIteration,ValueError):
            pass
    bm.to_mesh(data2);bm.free()
    if cap_studs:
        for i,co in enumerate((points[0],points[-1])):
            stud(name+'_Cap'+str(i),co,radius*1.25,mat,bone)
    return finish(mesh_obj,name,mat,bone)

def ring(name,center,r,tube,mat=GOLD,bone='Root',segments=40):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D'
    data.resolution_u=4;data.bevel_depth=tube;data.bevel_resolution=3
    spline=data.splines.new('POLY');spline.points.add(segments-1)
    for i,p in enumerate(spline.points):
        a=2*math.pi*i/segments
        p.co=(center[0]+r*math.cos(a),center[1]+r*math.sin(a),center[2],1)
    spline.use_cyclic_u=True
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object,name,mat,bone)

def arch_shell(name,x0,x1,outer_r,outer_h,inner_r,inner_h,outer_mat=IRON,inner_mat=INNER):
    # A closed-thickness arch, open underside; never a filled box or bottom plate.
    n=80;verts=[]
    for x in (x0,x1):
        for r,h in ((outer_r,outer_h),(inner_r,inner_h)):
            verts.extend((x,-r*math.cos(i*math.pi/n),99+h*math.sin(i*math.pi/n)) for i in range(n+1))
    def v(side,inner,i):return (side*2+inner)*(n+1)+i
    faces=[];ids=[]
    for i in range(n):
        faces += [(v(0,0,i),v(1,0,i),v(1,0,i+1),v(0,0,i+1)),
                  (v(0,1,i+1),v(1,1,i+1),v(1,1,i),v(0,1,i))]
        ids += [outer_mat,inner_mat]
        for side in (0,1):
            faces.append((v(side,0,i),v(side,0,i+1),v(side,1,i+1),v(side,1,i)));ids.append(outer_mat)
    for i in (0,n):
        faces.append((v(0,0,i),v(0,1,i),v(1,1,i),v(1,0,i)));ids.append(outer_mat)
    return raw(name,verts,faces,ids,'Lid')

def end_panel(name,x0,x1):
    n=80;arc=[(-73.5*math.cos(i*math.pi/n),99+57.5*math.sin(i*math.pi/n)) for i in range(n+1)]
    verts=[(x,y,z) for x in (x0,x1) for y,z in arc]
    faces=[tuple(range(n,-1,-1)),tuple(range(n+1,2*(n+1)))];ids=[IRON,IRON]
    for i in range(n+1):
        j=(i+1)%(n+1);faces.append((i,j,n+1+j,n+1+i));ids.append(IRON)
    return raw(name,verts,faces,ids,'Lid',smooth=False)
