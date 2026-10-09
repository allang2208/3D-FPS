"""Sew the rigid visor into the leather band; keep crown, hardware and head pivot."""
import bpy,bmesh,json,math,hashlib,struct
from pathlib import Path
from mathutils import Vector,Quaternion
B=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');R=B/'V14'
for d in ['Authoring','Delivery','Diagnosis','Logs']:(R/d).mkdir(parents=True,exist_ok=True)
source=json.loads((R/'Diagnosis/hat_before.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(B/'V11/Authoring/SecurityServiceCap_Anatomical_V11.blend'))
cap=bpy.data.objects['SM_SecurityServiceCap_V11'];cy=-.042
remove=set()
for island in source['islands']:
    if island['vertices'] in [640,1430] and island['materials']==['Security_Leather']:remove.update(island['ids'])
if len(remove)!=2070:raise RuntimeError('Source band/visor topology changed')
preserved_coords=sorted(tuple(v.co) for v in cap.data.vertices if v.index not in remove)
bm=bmesh.new();bm.from_mesh(cap.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in remove],context='VERTS');bm.to_mesh(cap.data);bm.free()
if sorted(tuple(v.co) for v in cap.data.vertices)!=preserved_coords:raise RuntimeError('Unrelated crown/detail positions changed')
cap.name='SM_SecurityServiceCap_V14'
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
angles=sorted(set(round(-math.pi+2*math.pi*i/80,9) for i in range(80))|
              set(round(-1.43+2.86*i/64,9) for i in range(65)))
front=[i for i,a in enumerate(angles) if -1.43-1e-8<=a<=1.43+1e-8]
N=len(angles);verts=[];faces=[]
def point(rx,ry,z,a):return (rx*math.sin(a),cy-ry*math.cos(a),z)
def add(p):verts.append(tuple(p));return len(verts)-1
outer=[];inner=[]
rings=[(.091,.108,1.745),(.092,.109,1.750),(.094,.112,1.768),(.094,.112,1.772)]
for j,(rx,ry,z) in enumerate(rings):outer.append([add(point(rx,ry,z,a)) for a in angles])
for j,(rx,ry,z) in enumerate(rings):inner.append([add(point(rx-.003,ry-.003,z-(.0035 if j==0 else 0),a)) for a in angles])
for j in range(3):
    for i in range(N):
        k=(i+1)%N
        faces.extend([(outer[j][i],outer[j][k],outer[j+1][k],outer[j+1][i]),
                      (inner[j][k],inner[j][i],inner[j+1][i],inner[j+1][k])])
for i in range(N):
    k=(i+1)%N;faces.append((outer[3][i],outer[3][k],inner[3][k],inner[3][i]))
    # Across the front, visor top/bottom replace the band bottom closure.
    if not (i in front and k in front and k==i+1):faces.append((outer[0][k],outer[0][i],inner[0][i],inner[0][k]))
top=[[outer[0][i] for i in front]];bottom=[[inner[0][i] for i in front]]
NY=14
for j in range(1,NY+1):
    t=j/NY;fade=(1-t)**2*(1+2*t);up=[];down=[]
    for i in front:
        a=angles[i]
        old=Vector((math.sin(a)*(.087+.008*t),cy-math.cos(a)*(.105+.066*t),1.748-.013*t-.010*math.sin(a)**2))
        old_root=Vector((.087*math.sin(a),cy-.105*math.cos(a),1.748-.010*math.sin(a)**2))
        new_root=Vector(verts[outer[0][i]])
        p=old+(new_root-old_root)*fade
        inset=Vector((-.003*math.sin(a),.003*math.cos(a),0))*fade
        up.append(add(p));down.append(add(p+inset+Vector((0,0,-.0035))))
    top.append(up);bottom.append(down)
for j in range(NY):
    for i in range(len(front)-1):
        faces.extend([(top[j][i],top[j][i+1],top[j+1][i+1],top[j+1][i]),
                      (bottom[j][i+1],bottom[j][i],bottom[j+1][i],bottom[j+1][i+1])])
    faces.append((top[j][0],top[j+1][0],bottom[j+1][0],bottom[j][0]))
    faces.append((top[j+1][-1],top[j][-1],bottom[j][-1],bottom[j+1][-1]))
for i in range(len(front)-1):faces.append((top[-1][i],top[-1][i+1],bottom[-1][i+1],bottom[-1][i]))
me=bpy.data.meshes.new('Security_SewnBandVisor_V14');me.from_pydata(verts,[],faces);me.materials.append(bpy.data.materials['Security_Leather']);me.update()
sewn=bpy.data.objects.new('Security_SewnBandVisor_V14',me);bpy.context.collection.objects.link(sewn)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
volume=bm.calc_volume(signed=True)
if volume<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces));volume=-volume
bad=[e for e in bm.edges if not e.is_manifold];zero=[f for f in bm.faces if f.calc_area()<1e-12]
if bad or zero:raise RuntimeError('Sewn hat shell is not closed/manifold: '+str((len(bad),len(zero))))
bm.to_mesh(me);bm.free();me.update()
for f in me.polygons:f.use_smooth=True
active(sewn);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
# Keep the stitched leather construction editable separately in a datablock.
source_part=sewn.copy();source_part.data=sewn.data.copy();source_part.name='SewnBandVisor_Source_V14';source_part.use_fake_user=True;source_part.data.use_fake_user=True
active(cap);sewn.select_set(True);bpy.ops.object.join();cap=bpy.context.object
cap.data.name='Security_ServiceCap_Joined_V14'
# Retain the old crown collider, replace only the visor collider to include the
# new attachment surface. Head-local origin and drop component remain unchanged.
crown_collision=bpy.data.objects['UCX_SM_SecurityServiceCap_V11_00'];crown_collision.name='UCX_SM_SecurityServiceCap_V14_00'
old_visor_collision=bpy.data.objects['UCX_SM_SecurityServiceCap_V11_01'];bpy.data.objects.remove(old_visor_collision,do_unlink=True)
collision_points=[verts[i] for layer in top+bottom for i in layer]
cm=bpy.data.meshes.new('Security_VisorConvex_V14');cm.from_pydata(collision_points,[],[])
bm=bmesh.new();bm.from_mesh(cm);bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cm);bm.free()
visor_collision=bpy.data.objects.new('UCX_SM_SecurityServiceCap_V14_01',cm);bpy.context.collection.objects.link(visor_collision);visor_collision.hide_render=True
colliders=[crown_collision,visor_collision]
recipe=json.loads((B/'V11/authoring_receipt.json').read_text(encoding='utf-8'))['hat']
report={'revision':'V14','source_hat':'V11','construction':'Single closed band/visor shell; shared top and bottom attachment rows; sealed side returns',
        'source_gap_mm':source['max_root_below_band_mm'],'shared_front_vertices_per_surface':len(front),
        'sewn_shell_nonmanifold_edges':len(bad),'sewn_shell_zero_area_faces':len(zero),'sewn_shell_volume_cm3':volume*1e6,
        'preserved_crown_and_detail_vertices':len(preserved_coords),'head_attachment':recipe,
        'game_tested':False,'rendered':False,'cpp_modified':False,'convex_collision_bodies':2}
active(cap)
for o in colliders:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Authoring/SecurityServiceCap_Anatomical_V14.blend'))
# Match the V11 delivery transformation exactly.
ref=json.loads((B/'V11/neck_source.json').read_text(encoding='utf-8'))['ue_head_reference']
q=ref['rotation_xyzw'];rotation=Quaternion((q[3],q[0],q[1],q[2]));origin=Vector(ref['translation_cm']);local_pivot=Vector(recipe['relative_location_cm'])
for o in [cap]+colliders:
    for v in o.data.vertices:
        p=v.co;ue=Vector((p.x*100,-p.y*100,p.z*100));local=rotation.inverted()@(ue-origin)-local_pivot
        v.co=Vector((local.x,-local.y,local.z))/100
    if o.data.has_custom_normals:o.data.normals_split_custom_set([(0.,0.,0.)]*len(o.data.loops))
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Authoring/SecurityServiceCap_EngineLocal_V14.blend'))
bpy.ops.export_scene.fbx(filepath=str(R/'Delivery/SM_SecurityServiceCap_V14.fbx'),use_selection=True,object_types={'MESH'},
    add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',use_mesh_modifiers=True)
report.update(triangles=sum(len(f.vertices)-2 for f in cap.data.polygons),materials=[m.name for m in cap.data.materials],stage='exported')
(R/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_HAT_V14_AUTHORED '+json.dumps(report),flush=True)
