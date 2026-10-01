"""Author a continuous A762 extended magazine, preserving its factory hardware."""
import bpy, bmesh, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector

O = Path(__file__).parent
sys.path.insert(0,str(O))
import curve as C
P = O.parents[1]
SOURCE = P/'SourceAssets/A762Meshy20260920/Refinement04/A762_StockJoint_Editable.blend'
F = json.loads((P/'SourceAssets/A762Meshy20260920/Accessories05/authoring_frames.json').read_text())
X = Matrix(F['mag_idle_from_root'])
(O/'Exports').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
r=bpy.data.objects['SK_M4_Infima']
r.animation_data.action=bpy.data.actions['A_A762_idle']
r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy()
xf=root.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix@r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()

# The mouth hardware and floorplate are true factory geometry, not generated
# replacements. Copy the actual corner normals before dropping the armature.
hardware=[]
for ob in bpy.data.collections['A762_RECONSTRUCTED_02'].objects:
    if ob.type!='MESH' or not ob.name.startswith('A762_R02_Magazine_'):continue
    if not any(k in ob.name for k in ('Floorplate','FeedLip','Follower','FrontCatch','RearCatch')):continue
    me=ob.data.copy()
    nn=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in me.corner_normals]
    me.transform(xf);me.normals_split_custom_set(nn)
    if 'Floorplate' in ob.name:
        offset=C.NEW[-1]-C.C[-1]
        me.transform(Matrix.Translation(Vector((0,float(offset[0]),float(offset[1])))))
    hardware.append((ob.name,me))
if len(hardware)!=6:raise RuntimeError('Unexpected factory hardware selection '+str(len(hardware)))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)

# Dedicated materials reproduce the already saved Refine06 assignments for
# the offline inspection. UE import binds the existing MI assets by slot name.
material_names=['M_A762_Magazine_Rebuilt','M_A762_MagazineInside_Rebuilt','M_A762_MagazineEdge_Rebuilt']
materials=[]
for name,col,metal,rough in [(material_names[0],(.029,.031,.033),1,.46),
                            (material_names[1],(.004,.004,.004),0,.75),
                            (material_names[2],(.033,.035,.037),1,.41)]:
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True;m.node_tree.nodes.clear()
    bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    materials.append(m)
objects=[]
for name,me in hardware:
    old=[m.name for m in me.materials];me.materials.clear()
    for label in old:me.materials.append(materials[material_names.index(label)])
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);objects.append(ob)

def ramp(x):
    x=np.clip(x,0.,1.);return x*x*(3-2*x)
def band(x,a,b,fade):
    return ramp((x-a)/fade)*ramp((b-x)/fade)
def relief(u,s):
    value=0.
    for a,b,t0,t1,h in [(.026,.071,.055,.99,.0009),(.155,.180,.08,.98,.0006),(.915,.952,.04,.99,.0006)]:
        value+=h*band(u,a,b,(b-a)*.22)*band(s,C.arc(t0),C.extended_s(t1),.0015)
    value+=.00018*band(u,.23,.85,.035)*band(s,C.arc(.15),C.extended_s(.92),.002)
    for centre in C.RIBS:
        value+=.001*band(s,centre-.0012,centre+.0012,.00045)*band(u,.035,.17,.025)
    return float(value)

# A single welded shell: longitudinal features are displacement of the side
# surface itself. There is no copied band, joining collar or overlapping panel.
us=set(np.linspace(.032,.968,43))
for a,b in [(.026,.071),(.155,.180),(.915,.952),(.23,.85),(.035,.17)]:
    for x in (a,a+(b-a)*.11,a+(b-a)*.22,b-(b-a)*.22,b-(b-a)*.11,b):
        if .027<x<.973:us.add(x)
us=sorted(us)
rows=set(np.linspace(0.,C.END,145))
rows.add(C.KEEP)
for s in C.RIBS:
    rows.update(s+v for v in (-.0012,-.000975,-.00075,0.,.00075,.000975,.0012))
rows=sorted(rows)
rad=.0017;hw=.0112;cx=.00056

def perimeter(s,width=hw,inset=0.,features=True):
    centre,direction,half=C.at(s);half=float(half)-inset
    # CCW in (width, section-depth), following the factory rounded section.
    pts=[]
    for a in np.linspace(0,90,7):
        t=math.radians(a);pts.append((width-rad+rad*math.cos(t),half-rad+rad*math.sin(t)))
    for a in np.linspace(90,180,7):
        t=math.radians(a);pts.append((-width+rad+rad*math.cos(t),half-rad+rad*math.sin(t)))
    for u in reversed(us):
        depth=half*(2*u-1)
        if abs(depth)<half-rad:pts.append((-width-(relief(u,s) if features else 0),depth))
    for a in np.linspace(180,270,7):
        t=math.radians(a);pts.append((-width+rad+rad*math.cos(t),-half+rad+rad*math.sin(t)))
    for a in np.linspace(270,360,7):
        t=math.radians(a);pts.append((width-rad+rad*math.cos(t),-half+rad+rad*math.sin(t)))
    for u in us:
        depth=half*(2*u-1)
        if abs(depth)<half-rad:pts.append((width+(relief(u,s) if features else 0),depth))
    return [(cx+x,*(centre+direction*y)) for x,y in pts]

# Use a fixed normalized side domain for every ring, including narrow ends.
# Remove side samples that cannot fit the smallest rounded section.
min_half=min(float(C.at(s)[2]) for s in rows)-.003
us=[u for u in us if abs(2*u-1)<1-rad/min_half]
verts=[];faces=[];face_material=[];uv_coords=[];planar_faces={}
count=len(perimeter(0))
for s in rows:
    ring=perimeter(s)
    if len(ring)!=count:raise RuntimeError('Inconsistent section sampling')
    rp=np.array(ring);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(rp,axis=0),axis=1))]
    verts.extend(ring);uv_coords.extend([(float(v)*35.,float(s)*35.) for v in dist])
for j in range(len(rows)-1):
    for i in range(count):
        faces.append((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i));face_material.append(0)
# Fan caps avoid the nearly collinear ear triangles an n-gon tessellator can
# create along the densely sampled straight sides of a rounded rectangle.
bottom_center=len(verts);c,_,_=C.at(C.END)
verts.append((cx,*c));uv_coords.append((0,0))
for i in range(count):
    planar_faces[len(faces)]=C.END
    faces.append(((len(rows)-1)*count+i,(len(rows)-1)*count+(i+1)%count,bottom_center));face_material.append(0)
# Recessed throat, lip wall and floor use the same loop connectivity.
inside=[]
for s in (0.,C.arc(.065)):
    start=len(verts);ring=perimeter(s,.0088,.003,False)
    if len(ring)!=count:raise RuntimeError('Inner section count changed')
    inside.append(start);verts.extend(ring)
    uv_coords.extend([(i/count,s*35.) for i in range(count)])
for i in range(count):
    j=(i+1)%count
    planar_faces[len(faces)]=0.
    faces.extend([(i,j,inside[0]+j,inside[0]+i),(inside[0]+i,inside[0]+j,inside[1]+j,inside[1]+i)])
    face_material.extend((2,1))
inner_center=len(verts);c,_,_=C.at(C.arc(.065))
verts.append((cx,*c));uv_coords.append((0,0))
for i in range(count):
    planar_faces[len(faces)]=C.arc(.065)
    faces.append((inside[1]+i,inside[1]+(i+1)%count,inner_center));face_material.append(1)
me=bpy.data.meshes.new('A762_ContinuousMagazineShell');me.from_pydata(verts,[],faces);me.update()
for m in materials:me.materials.append(m)
uv=me.uv_layers.new(name='UV0')
for p in me.polygons:
    p.material_index=face_material[p.index]
    for li in p.loop_indices:uv.data[li].uv=uv_coords[me.loops[li].vertex_index]
# Caps and the mouth annulus need planar UVs; a constant arc coordinate would
# collapse their UV triangles and prevent a valid tangent basis on the rim.
body_faces=(len(rows)-1)*count
for p in me.polygons:
    if p.index in planar_faces:
        s=planar_faces[p.index]
        centre,direction,_=C.at(s)
        for li in p.loop_indices:
            co=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(co.x*35.,float(np.dot(np.array((co.y,co.z))-centre,direction))*35.)
# Place the single circumferential UV seam on the narrow front edge. Avoid
# interpolation across a whole UV tile at its wrap.
for p in me.polygons:
    if len(p.vertices)==4 and p.index<(len(rows)-1)*count and p.index%count==count-1:
        for li in p.loop_indices:
            if me.loops[li].vertex_index%count==0:
                row=me.loops[li].vertex_index//count
                ring=np.array(verts[row*count:(row+1)*count])
                length=np.linalg.norm(np.diff(np.vstack((ring,ring[:1])),axis=0),axis=1).sum()
                uv.data[li].uv.x=float(length)*35.
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for f in bm.faces:f.smooth=True
for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(38))
bm.to_mesh(me);bm.free();me.update()
ob=bpy.data.objects.new('A762_ContinuousMagazineShell',me);bpy.context.scene.collection.objects.link(ob);objects.append(ob)
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
mod=ob.modifiers.new('Mouth and floor edge radius','BEVEL');mod.width=.00012;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(50);mod.use_clamp_overlap=True
bpy.ops.object.modifier_apply(modifier=mod.name)
mod=ob.modifiers.new('Preserve broad side planes','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
bpy.ops.object.modifier_apply(modifier=mod.name)

# Save only the finished magazine in the exact original magazine socket frame.
for ob in objects:
    normals=[(X.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
    ob.data.transform(X);ob.data.normals_split_custom_set(normals)
    ob.select_set(True)
# Write only local finished objects, then reopen them in an empty scene. The
# factory author file contains linked arm rigs whose collection overrides can
# otherwise reappear on reload despite having been removed from the scene.
names=[ob.name for ob in objects]
stage=O/'MagazineObjects.blend'
bpy.data.libraries.write(str(stage),set(objects),path_remap='ABSOLUTE')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(stage),link=False) as (data_from,data_to):
    data_to.objects=names
objects=list(data_to.objects)
for ob in objects:bpy.context.scene.collection.objects.link(ob);ob.select_set(True)
for ob in objects:
    bpy.context.view_layer.objects.active=ob
    tri=ob.modifiers.new('Explicit export triangulation','TRIANGULATE')
    tri.quad_method='BEAUTY';tri.ngon_method='BEAUTY'
    if hasattr(tri,'keep_custom_normals'):tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.context.view_layer.objects.active=objects[-1]
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_A762_ext_mag_Continuous07.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_ExtMag_Continuous07.blend'))
report=C.report();report.update({'source':str(SOURCE),'objects':[ob.name for ob in objects],
    'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in objects),
    'shell_single_connected_surface':True,'material_slots':material_names,'runtime_tested':False})
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('A762_EXTMAG_AUTHORED',report['triangles'],flush=True)
