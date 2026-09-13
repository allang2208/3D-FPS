"""Replace only the panoramic adapter with a rounded, fitted one-piece saddle."""
import bpy,bmesh,math,json,ast
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
slide=bpy.data.objects['M1911_Slide']
surface=BVHTree.FromPolygons([root.inverted() @ slide.matrix_world @ v.co for v in slide.data.vertices],
                           [list(p.vertices) for p in slide.data.polygons])
bpy.ops.wm.open_mainfile(filepath=str(S/'M1911MuzzleRedDot20260913/M1911_panoramic_red_dot_Editable.blend'))
original=bpy.data.objects['M1911_panoramic_red_dot']
for ob in list(bpy.context.scene.objects):
    if ob!=original:bpy.data.objects.remove(ob,do_unlink=True)
old=original.data;adapter_index=next(i for i,m in enumerate(old.materials) if 'AdapterSteel' in m.name)
steel=old.materials[adapter_index]

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def mesh_object(name,verts,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material)
    return ob

def physical_uv(ob,index):
    me=ob.data
    while len(me.uv_layers)<=index:me.uv_layers.new(name='UV'+str(len(me.uv_layers)))
    uv=me.uv_layers[index];uv.name='M1911CoatingPhysicalUV' if index else 'UVMap'
    for face in me.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.1+.5,p[axes[1]]/.1+.5)

def bevel(ob,width,segments=3):
    select(ob);mod=ob.modifiers.new('Machined fillets','BEVEL');mod.width=width;mod.segments=segments;mod.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=mod.name)

def subtract(ob,cutter):
    if not cutter.data.materials:cutter.data.materials.append(steel)
    select(ob);mod=ob.modifiers.new('Recess machining','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def cylinder(name,position,radius,depth,vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=position,rotation=(math.pi/2,0,0))
    ob=bpy.context.object;ob.name=name;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return ob

# Copy the optical/body subset explicitly, including every retained UV and split
# normal. Removing the former adapter must not resmooth the accepted optical frame.
polys=[p for p in old.polygons if p.material_index!=adapter_index]
used=sorted({vi for p in polys for vi in p.vertices});mapping={vi:i for i,vi in enumerate(used)}
me=bpy.data.meshes.new('PanoramicOpticalBodyPreserved')
me.from_pydata([old.vertices[vi].co for vi in used],[],[[mapping[vi] for vi in p.vertices] for p in polys]);me.update()
for material in old.materials:me.materials.append(material)
normals=[]
for new_face,old_face in zip(me.polygons,polys):
    new_face.material_index=old_face.material_index;new_face.use_smooth=old_face.use_smooth
    normals.extend(old.corner_normals[li].vector.copy() for li in old_face.loop_indices)
for old_uv in old.uv_layers:
    new_uv=me.uv_layers.new(name=old_uv.name)
    for new_face,old_face in zip(me.polygons,polys):
        for new_li,old_li in zip(new_face.loop_indices,old_face.loop_indices):new_uv.data[new_li].uv=old_uv.data[old_li].uv
for attr in old.color_attributes:
    new=me.color_attributes.new(name=attr.name,type=attr.data_type,domain=attr.domain)
    if attr.domain=='CORNER':
        for new_face,old_face in zip(me.polygons,polys):
            for new_li,old_li in zip(new_face.loop_indices,old_face.loop_indices):new.data[new_li].color=attr.data[old_li].color
    else:
        for old_vi,new_vi in mapping.items():new.data[new_vi].color=attr.data[old_vi].color
me.normals_split_custom_set(normals);original.data=me

def outline(hx,hy,r):
    points=[]
    for cx,cy,angle in [(hx-r,hy-r,0),(-hx+r,hy-r,90),(-hx+r,-hy+r,180),(hx-r,-hy+r,270)]:
        for i in range(12):
            a=math.radians(angle+i*90/12);points.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return points

# Rounded planform and a swept shoulder replace the flat plate/straight legs.
# Width peaks at 24.8 mm and narrows toward the actual slide-contact footprint.
levels=[(0,.016,.0108,.003),(.16,.0163,.0109,.003),(.35,.0171,.01135,.003),
        (.55,.0182,.01195,.003),(.74,.019,.0124,.003),(.88,.019,.0124,.003),
        (.96,.0188,.0122,.003),(1,.0183,.0117,.003)]
verts=[];rings=[]
for t,hx,hy,r in levels:
    ring=[]
    for x,y in outline(hx,hy,r):
        bx=x*levels[0][1]/hx;by=y*levels[0][2]/hy
        hit,_,_,_=surface.ray_cast(Vector((by,.030-bx,.08)),Vector((0,0,-1)),.07)
        if hit is None:raise RuntimeError('No slide contact for sculpted saddle')
        floor=hit.z-.0495-.00012
        ring.append(len(verts));verts.append((x,y,floor*(1-t)))
    rings.append(ring)
n=len(rings[0]);faces=[tuple(reversed(rings[0])),tuple(rings[-1])]
for a,b in zip(rings,rings[1:]):
    for i in range(n):faces.append((a[i],a[(i+1)%n],b[(i+1)%n],b[i]))
saddle=mesh_object('M1911_SculptedSaddle',verts,faces,steel)
# Round the underside tunnel so the retained rear iron sight has clearance.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.0222));cutter=bpy.context.object
cutter.dimensions=(.06,.015,.04);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bevel(cutter,.0012,6);subtract(saddle,cutter)
bevel(saddle,.00025,4)

# Four recessed low-profile fasteners. Heads stay below the curved side surface;
# the recesses and socket pockets supply detail without increasing mount width.
parts=[saddle]
for side in [-1,1]:
    for x in [-.010,.010]:
        z=-.0035
        bvh=BVHTree.FromPolygons([v.co for v in saddle.data.vertices],[list(f.vertices) for f in saddle.data.polygons])
        hit,_,_,_=bvh.ray_cast(Vector((x,side*.025,z)),Vector((0,-side,0)),.02)
        if hit is None:raise RuntimeError('No saddle side for recessed fastener')
        recess=cylinder('Counterbore',(x,hit.y-side*.00015,z),.00135,.00075)
        subtract(saddle,recess)
        head=cylinder('RecessedSocketHead',(x,hit.y-side*.00029,z),.00108,.00022)
        head.data.materials.append(steel);bevel(head,.00007,3)
        pocket=cylinder('HexSocket',(x,hit.y-side*.00017,z),.00048,.00030,6)
        subtract(head,pocket);parts.append(head)
for ob in parts:
    for face in ob.data.polygons:face.use_smooth=abs(face.normal.z)<.99
    select(ob);weighted=ob.modifiers.new('Weighted planar highlights','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=35
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    physical_uv(ob,0);physical_uv(ob,3)
select(original)
for ob in parts:ob.select_set(True)
bpy.ops.object.join();ob=original;ob.name='M1911_panoramic_red_dot'
triangulate=ob.modifiers.new('Export triangulation','TRIANGULATE')
triangulate.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=triangulate.name)
ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
for name,point in {'AimCenter':(.013175,0,.02015),'MountForward':(.03,0,0),'MountUp':(0,0,.03)}.items():
    socket=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(socket);socket.parent=ob;socket.location=point;socket.select_set(True)
file=O/'SM_M1911_panoramic_red_dot.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
                        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
ob.hide_render=False;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_SculptedMount_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'fbx':str(file),'source':'M1911MuzzleRedDot20260913/M1911_panoramic_red_dot_Editable.blend',
    'adapter_max_width_m':.0248,'coating_uv':3,'physical_tile_m':.1,'mount_root_m':[0,.030,.0495],
    'aim_point_ue_cm':[1.3175,0,2.015],'reticle':'previous enlarged geometry retained',
    'details':'rounded lofted shoulder, curved slide footprint, radiused rear-sight tunnel, four recessed socket heads',
    'slots':[m.name for m in ob.data.materials]},indent=2))
print('M1911_SCULPTED_MOUNT_AUTHORED',flush=True)
