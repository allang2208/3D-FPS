"""Author a contoured upper saddle from the actual M4 receiver and fitted grip surfaces."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Seam_Authoring_Source.blend'))
grip=bpy.data.objects['SM_BalancedRearGrip'];receiver=bpy.data.objects['Receiver_M4_M4 Body_Export']
def tree(ob,body_only=False):
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[tuple(f.vertices) for f in ob.data.polygons if not body_only or 'Collar' not in ob.data.materials[f.material_index].name])
g=tree(grip,True);r=tree(receiver)
def griptop(x,y):
    p=g.ray_cast(Vector((x,y,.05)),Vector((0,0,-1)),.1)[0]
    return p.z if p and p.z>.003 else None
def roof(x,y):
    p=r.ray_cast(Vector((x,y,.018)),Vector((0,0,1)),.06)[0]
    return p.z if p else None
ys=np.linspace(-.024,.0355,43);us=np.linspace(-1,1,13);rows=[];verts=[]
for y in ys:
    # Receiver saddle narrows at its front underside. Avoid reaching the upper
    # receiver sidewall when a sample lies outside the lower mating face.
    upper=.0111 if y<.031 else float(np.interp(y,[.031,.0355],[.0111,.0088]))
    while upper>.007:
        ztops=[roof(float(u*upper),float(y)) for u in us]
        if all(z is not None and z<.047 for z in ztops):break
        upper-=.0002
    if any(z is None for z in ztops):raise RuntimeError('Cannot author saddle outside receiver surface')
    lower=.0142
    while lower>.008 and (griptop(-lower,float(y)) is None or griptop(lower,float(y)) is None):lower-=.0003
    if y<-.0225:lower=.0121
    bottoms=[griptop(float(u*lower),float(y)) for u in us]
    valid=[i for i,z in enumerate(bottoms) if z is not None]
    for j,u in enumerate(us):
        # The generated rear tang has a hollow centre. A shallow internal floor
        # ties its two sides together while the roof follows the receiver recess.
        bottom=bottoms[j]
        if bottom is None:bottom=float(np.interp(j,valid,[bottoms[k] for k in valid]))-.003 if valid else .012
        bottom=min(bottom-.0012,ztops[j]-.002)
        verts.append((float(u*lower),float(y),float(bottom)))
    for j,u in enumerate(us):verts.append((float(u*upper),float(y),float(ztops[j]+.0008)))
    rows.append({'y_m':float(y),'lower_halfwidth_m':lower,'upper_halfwidth_m':upper})
nx=len(us);stride=nx*2;faces=[];smooth=[]
for row in range(len(ys)-1):
    a=row*stride;b=(row+1)*stride
    for col in range(nx-1):
        faces.append((a+col,b+col,b+col+1,a+col+1));smooth.append(False)
        faces.append((a+nx+col,a+nx+col+1,b+nx+col+1,b+nx+col));smooth.append(True)
    faces.append((a,a+nx,b+nx,b));smooth.append(True)
    faces.append((a+nx-1,b+nx-1,b+stride-1,a+stride-1));smooth.append(True)
for row in [0,len(ys)-1]:
    a=row*stride
    for col in range(nx-1):
        f=(a+col,a+col+1,a+nx+col+1,a+nx+col)
        faces.append(f if row==0 else tuple(reversed(f)));smooth.append(False)
mesh=bpy.data.meshes.new('M4_Receiver_Grip_Saddle');mesh.from_pydata(verts,[],faces);mesh.update()
bridge=bpy.data.objects.new('M4_Contoured_Seam_Bridge',mesh);bpy.context.collection.objects.link(bridge)
for f,s in zip(mesh.polygons,smooth):f.use_smooth=s
bridge.data.materials.append(next(m for m in grip.data.materials if 'Collar' in m.name))
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
active(bridge)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
bev=bridge.modifiers.new('Soft mating edges','BEVEL');bev.width=.00025;bev.segments=3;bev.limit_method='ANGLE';bev.angle_limit=math.radians(35)
bpy.ops.object.modifier_apply(modifier=bev.name)
bm=bmesh.new();bm.from_mesh(bridge.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(bridge.data);bm.free()
# Match both existing UV names/order. M4 receiver finish uses UV1 at 12 x 5 cm.
for index,source_uv in enumerate(grip.data.uv_layers):
    uv=bridge.data.uv_layers.new(name=source_uv.name)
    for face in bridge.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(face.normal[j]))]
        for li in face.loop_indices:
            co=bridge.data.vertices[bridge.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/.12,co[axes[1]]/.05) if index==1 else (co[axes[0]]/.1,co[axes[1]]/.1)
for attr in grip.data.color_attributes:
    colors=bridge.data.color_attributes.new(name=attr.name,type=attr.data_type,domain=attr.domain)
    for value in colors.data:value.color=(1,1,1,1)
    bridge.data.color_attributes.active_color=colors
added=sum(len(f.vertices)-2 for f in bridge.data.polygons)
# Keep an editable separate bridge and receiver reference in the author scene.
bridge_source=bridge.copy();bridge_source.data=bridge.data.copy();bpy.context.collection.objects.link(bridge_source);bridge_source.name='Bridge_Editable_Separate';bridge_source.hide_set(True);bridge_source.hide_render=True
active(grip);bridge.select_set(True);bpy.ops.object.join()
grip.data.uv_layers.active_index=0;grip.data.uv_layers[0].active_render=True
for ob in bpy.context.scene.objects:
    if ob!=grip:ob.hide_set(True);ob.hide_render=True
active(grip);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'M4_BalancedRearGrip_Seam_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'SM_BalancedRearGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
(P/'authoring.json').write_text(json.dumps({'source':'RearGripFinish20260913/M4/balanced/ForwardFit/Editable.blend','family':'M4','attachment_id':'balanced_reargrip','body_position':'unchanged; retains prior forward 5 mm fit','bridge_added_triangles':added,'total_triangles':sum(len(f.vertices)-2 for f in grip.data.polygons),'receiver_overlap_m':.0008,'grip_overlap_m':.0012,'receiver_material':'/Game/Weapons/RearGripFinish20260913/M4/balanced/M_M4_balanced_Collar','coating_uv':1,'coating_tile_m':[.12,.05],'rows':rows,'runtime_tested':False,'preview_rendered':False},indent=2))
print('M4_BALANCED_BRIDGE_EXPORTED',added,flush=True)
