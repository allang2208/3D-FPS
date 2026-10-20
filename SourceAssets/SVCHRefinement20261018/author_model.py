"""Weld source normal seams, machine edges and separate SVCh surface identities.

Keeps the selected Sketchfab silhouette and native arm rig. Blender background.
"""
import bpy, bmesh, json, gzip, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
import numpy as np

O=Path(__file__).parent
SRC=O.parent/'SVCHSketchfab20261017'
OUT=O/'Exports'; OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Authoring/SVCH_Viewmodel.blend'))
rig=bpy.data.objects['SK_M4_Infima']
rig.animation_data_clear(); rig.data.pose_position='REST'
hold=json.loads((SRC/'Authoring/hold_frame.json').read_text())
HR=np.array(hold['R']); HT=np.array(hold['t_cm'])
audit=json.loads((SRC/'audit/measurements.json').read_text())
islands=audit['scene_inventory']['islands']
report={'source':str(SRC/'Authoring/SVCH_Viewmodel.blend'),'parts':{},'runtime_tested':False}
contact_meshes={}
S=Matrix.Diagonal(Vector((1,-1,1,1)))
def mat(n):
    m=bpy.data.materials.get(n) or bpy.data.materials.new(n)
    m.use_nodes=True
    return m
def record_mesh(ob):
    ob.data.calc_loop_triangles()
    return {'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles)}
def classify(component):
    # Blender -> UE bind centimetres -> source raw GLB -> audited source frame.
    p=np.array([[v.co.x*100,-v.co.y*100,v.co.z*100] for v in component])
    g=(p-HT)@HR
    a=np.column_stack((g[:,0]+18.7444,g[:,2],g[:,1]+1.5268))
    lo,hi=a.min(0),a.max(0)
    nearest=min(islands,key=lambda i:np.linalg.norm(lo-i['bbox_native_units']['min'])+np.linalg.norm(hi-i['bbox_native_units']['max']))
    error=float(np.linalg.norm(lo-nearest['bbox_native_units']['min'])+np.linalg.norm(hi-nearest['bbox_native_units']['max']))
    name=nearest['part'] if error<.08 else 'unclassified body'
    if name=='pistol grip' or name=='stock hinge / cheek riser': return 'Polymer',name,error
    if name=='butt plate': return 'Rubber',name,error
    if 'barrel' in name and 'handguard' not in name: return 'BarrelSteel',name,error
    return 'Body',name,error

for ob in list(bpy.data.objects):
    if ob.type!='MESH' or not ob.name.startswith('SM_SVCH_'): continue
    part=ob.name.removeprefix('SM_SVCH_')
    before=record_mesh(ob)
    bm=bmesh.new(); bm.from_mesh(ob.data)
    # glTF duplicates vertices for split normals; smooth shading cannot cross
    # those seams until positions are welded within this one mechanical part.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges))
    bm.normal_update()
    after_weld=len(bm.verts)
    materials=[part]
    shells=[]
    if part=='Body':
        materials=['Body','Polymer','Rubber','BarrelSteel']
        remaining=set(bm.verts)
        while remaining:
            seed=remaining.pop(); component={seed}; stack=[seed]
            while stack:
                for edge in stack.pop().link_edges:
                    # The edge's two ends are sufficient for a connected walk.
                    for v in edge.verts:
                        if v in remaining: remaining.remove(v);component.add(v);stack.append(v)
            surface,name,error=classify(component)
            faces={f for v in component for f in v.link_faces}
            if name in ('pistol grip','handguard shell (5 slots)','trigger'):
                verts=list(component); ids={v:i for i,v in enumerate(verts)}
                contact_meshes[name]={'positions':[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in verts],
                  'triangles':[[ids[v] for v in reversed(list(f.verts))] for f in faces]}
            for f in faces: f.material_index=materials.index(surface)
            shells.append({'name':name,'surface':surface,'triangles':len(faces),'match_error_cm':round(error,5)})
    hard=[e for e in bm.edges if e.is_manifold and e.calc_face_angle(0)>math.radians(40)]
    # Thin sight apertures and cartridges retain their exact openings. Chamfer
    # the body/rail only at 0.25 mm and mechanical parts at 0.15 mm.
    width=.00025 if part in ('Body','Magazine') else .00015
    if part=='Cartridge': width=0
    if width and hard:
        # BMesh's default material can put newly generated bevels back in slot
        # zero. Each disconnected shell keeps its own physical surface identity.
        hard_by_material={}
        for edge in hard:hard_by_material.setdefault(edge.link_faces[0].material_index,[]).append(edge)
        for material,edges in hard_by_material.items():
            bmesh.ops.bevel(bm,geom=[e for e in edges if e.is_valid],offset=width,segments=2,profile=.5,
                            affect='EDGES',clamp_overlap=True,loop_slide=True,material=material)
    # Clamped bevels at already thin corners can create coincident vertices
    # and collinear sliver faces. Clean after bevel and fix the triangulation
    # here so the FBX exporter and UE do not choose different diagonals.
    pre_cleanup={'vertices':len(bm.verts),'faces':len(bm.faces)}
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges))
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    collapsed=[f for f in bm.faces if f.calc_area()<5e-13]
    if collapsed:bmesh.ops.delete(bm,geom=collapsed,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.normal_update()
    for f in bm.faces: f.smooth=True
    for e in bm.edges: e.smooth=e.is_manifold and e.calc_face_angle(math.pi)<math.radians(35)
    ob.data.materials.clear()
    for label in materials: ob.data.materials.append(mat('SVCH_'+label))
    # Clearing material slots resets polygon indices; establish the slot array
    # BEFORE writing the classified faces back from BMesh.
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    # All new bevel vertices must receive this part's rigid weight; the source
    # script assigned weights before bevel and reported only the old counts.
    bone='WPN_bolt' if part=='BoltCarrier' else 'WPN_SOCKET_Magazine' if part in ('Magazine','Cartridge') else 'WPN_root'
    ob.vertex_groups.clear(); ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
    for mod in list(ob.modifiers): ob.modifiers.remove(mod)
    # Stable split normals retain broad flat machined faces around narrow bevels.
    wn=ob.modifiers.new('AreaWeightedMachinedNormals','WEIGHTED_NORMAL')
    wn.keep_sharp=True; wn.weight=50
    bpy.context.view_layer.objects.active=ob
    ob.select_set(True)
    dg=bpy.context.evaluated_depsgraph_get()
    finished=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
    ob.modifiers.clear(); ob.data=finished
    uv=ob.data.uv_layers.get('UVMap') or ob.data.uv_layers.new(name='UVMap')
    for f in ob.data.polygons:
        axis=max(range(3),key=lambda k:abs(f.normal[k]))
        a,b=[k for k in range(3) if k!=axis]
        for li in f.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(p[a]/.25,p[b]/.25)
    ob.modifiers.new('NativeRigidBinding','ARMATURE').object=rig
    report['parts'][part]={'before':before,'welded_vertices':after_weld,'bevel_edges':len(hard),
                         'bevel_mm':width*1000,'after':record_mesh(ob),'bone':bone,'surfaces':materials,'shells':shells,
                         'post_bevel_cleanup':{'before':pre_cleanup,'removed_collapsed_triangles':len(collapsed)}}

# Restore the donor's actual UV0 and split normals on the unchanged arm topology.
# Re-projecting skin with cube_project destroyed its atlas coordinates.
vm=json.load(gzip.open(SRC/'Donor/vm.json.gz','rt',encoding='utf-8'))
tri=np.array(vm['triangles']).reshape(-1,3)
faces=[i for i,m in enumerate(vm['material']) if vm['slots'][m] in ('MI_Manny_01','MI_Manny_02')]
arms=bpy.data.objects['SVCH_BareArmsV9']; me=arms.data
# The original author applied the glTF winding conversion to a native UE mesh
# as well. Its saved triangles were all reversed against the donor, despite
# matching vertex positions and UVs. Preserve donor winding through FBX.
used=sorted({int(v) for source in faces for v in tri[source]})
assert len(used)==len(me.vertices)
me.flip_normals()
uv=me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name='UVMap')
srcuv=np.array(vm['uv0']).reshape(-1,3,2)
srcn=np.array(vm['normals']).reshape(-1,3,3)
norm=[]
for f,source in zip(me.polygons,faces):
    f.use_smooth=True
    for li in f.loop_indices:
        source_vertex=used[me.loops[li].vertex_index]
        c=list(tri[source]).index(source_vertex)
        uv.data[li].uv=(srcuv[source,c,0],1-srcuv[source,c,1])
        x,y,z=srcn[source,c]; norm.append((x,-y,z))
me.normals_split_custom_set(norm)
report['arms']={'triangles':len(faces),'uv0':'restored donor per-corner atlas','normals':'restored donor split normals','weights':'unchanged','winding':'restored native UE winding (not the glTF source convention)'}

# Re-seat moving parts in the donor's ACTUAL saved idle, using UE ref transforms.
# Their bind origins are different from WPN_root, so assigning the same world
# vertices to the magazine/bolt bones without this inverse displaced them.
inputs=json.loads((O/'runtime_inputs.json').read_text())
ref=inputs['meshes']['svch']; names=inputs['meshes']['svd']['names']; parents=inputs['meshes']['svd']['parents']
def mx(row):
    return Matrix.LocRotScale(Vector(row[:3]),Quaternion((row[6],*row[3:6])),Vector(row[7:]))
R={n:mx(t) for n,t in zip(ref['names'],ref['component'])}
P={}
for n,parent,t in zip(names,parents,inputs['clips']['idle']['frames'][0]): P[n]=(P[parent]@mx(t)) if parent in P else mx(t)
root_delta=P['WPN_root']@R['WPN_root'].inverted()
for ob in bpy.data.objects:
    if ob.type!='MESH' or not ob.name.startswith('SM_SVCH_'): continue
    bone=ob.vertex_groups[0].name
    if bone=='WPN_root':continue
    correction=(P[bone]@R[bone].inverted()).inverted()@root_delta
    # Component space centimetres -> Blender metres; conjugate the handedness.
    correction.translation/=100
    ob.data.transform(S@correction@S)
    report['parts'][ob.name.removeprefix('SM_SVCH_')]['seat_correction_ue_cm']=[list(r) for r in (P[bone]@R[bone].inverted()).inverted()@root_delta]

rig.data.pose_position='POSE'
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
    if ob==rig or ob.type=='MESH': ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_Refined.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_SVCH_Refined.fbx'),use_selection=True,
 object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
 bake_anim=False,mesh_smooth_type='OFF',use_tspace=False)
(O/'model_receipt.json').write_text(json.dumps(report,indent=1),encoding='utf-8')
(O/'contact_meshes.json').write_text(json.dumps(contact_meshes),encoding='utf-8')
print('SVCH_MODEL_SAVED',json.dumps({p:d['after'] for p,d in report['parts'].items()}),flush=True)
