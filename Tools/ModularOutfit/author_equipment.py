"""Offline garment fitting and per-rig bound derivatives. No preview or runtime tests."""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
EXPORT=ROOT/'Exports'; EXPORT.mkdir(exist_ok=True)
INPUTS=json.loads((ROOT/'inputs.json').read_text())
REPORT=json.loads((ROOT/'authored.json').read_text()) if (ROOT/'authored.json').exists() else {}
ONLY=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def load(key):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=INPUTS[key]['fbx'],use_anim=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    mesh=next(o for o in bpy.data.objects if o.type=='MESH')
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    rig.data.pose_position='REST'
    return rig,mesh

def bone_world(rig):
    # Vertices here are already in physical metres. FBX bone matrices may still
    # carry a 0.01/1.0 unit basis; applying that ratio again would enlarge sleeves
    # 100 times. Strip units only from the authoring frame, never from the rig.
    result={}
    for b in rig.data.bones:
        raw=rig.matrix_world@b.matrix_local
        frame=raw.to_3x3().normalized().to_4x4();frame.translation=raw.translation
        result[b.name]=frame
    return result

def weights(obj,v):
    return {obj.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>0.0001}

def arm_weight(w):return sum(v for n,v in w.items() if any(s in n for s in ('upperarm','lowerarm','hand_','thumb_','index_','middle_','ring_','pinky_')))
def hand_weight(w):return sum(v for n,v in w.items() if any(s in n for s in ('hand_','thumb_','index_','middle_','ring_','pinky_')))

def make_mesh(name,coords,faces,vertex_weights,uvs=None,material_ids=None,materials=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(coords,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    groups={n:obj.vertex_groups.new(name=n) for w in vertex_weights for n in w if not obj.vertex_groups.get(n)}
    for i,w in enumerate(vertex_weights):
        norm=sum(w.values()) or 1
        for n,v in w.items():obj.vertex_groups[n].add([i],v/norm,'REPLACE')
    for name in materials or ['Fabric']:
        mesh.materials.append(bpy.data.materials.get(name) or bpy.data.materials.new(name))
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        p.use_smooth=True
        if material_ids:p.material_index=material_ids[p.index]
        for j,li in enumerate(p.loop_indices):
            uv.data[li].uv=uvs[p.index][j] if uvs else (coords[mesh.loops[li].vertex_index][0],coords[mesh.loops[li].vertex_index][2])
    return obj

def bind(obj,rig):
    obj.parent=rig;obj.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=obj.modifiers.new('AcceptedPose','ARMATURE');mod.object=rig

def export(obj,rig,name):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')),use_selection=True,
        object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='STRIP')

body_rig,body=load('Body')
BODY_BONES=bone_world(body_rig)
body.data.calc_loop_triangles()
bcoords=[body.matrix_world@v.co for v in body.data.vertices]
bweights=[weights(body,v) for v in body.data.vertices]
btris=[tuple(t.vertices) for t in body.data.loop_triangles]
bvh=BVHTree.FromPolygons(bcoords,btris,all_triangles=True)

def transfer(point):
    nearest,normal,ti,d=bvh.find_nearest(point)
    tri=btris[ti];a,b,c=(bcoords[i] for i in tri)
    bc=barycentric_transform(nearest,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    out={}
    for vi,f in zip(tri,bc):
        for n,w in bweights[vi].items():out[n]=out.get(n,0)+max(0,f)*w
    out=dict(sorted(out.items(),key=lambda x:-x[1])[:8]);s=sum(out.values())
    return {n:w/s for n,w in out.items()},nearest,normal,d

bpy.ops.wm.obj_import(filepath=str(ROOT/'Donor/sweater_fisherman.obj'))
donor=bpy.context.object
if donor is None or donor.type!='MESH':donor=next(o for o in bpy.data.objects if o.type=='MESH' and o!=body)
# MakeHuman hm08 garment is in decimetres around pelvis; fit arm landmarks
# continuously, keeping the native garment topology and UV seams.
source_s=Vector((.18,-.022, .555)); source_e=Vector((.35,-.039,.400)); source_h=Vector((.49,-.173,.284))
coords=[];vweights=[]
for v in donor.data.vertices:
    p=(donor.matrix_world@v.co)*.1
    side='l' if p.x>=0 else 'r';sign=1 if p.x>=0 else -1
    x=abs(p.x)
    # Fit the torso from hem to collar, and the sleeves from shoulder to cuff.
    torso=Vector((p.x*1.10,p.y, .91+(p.z-.11552)*(.625/(.69335-.11552))))
    if x>.145:
        ss=source_s.copy();se=source_e.copy();sh=source_h.copy()
        ss.x*=sign;se.x*=sign;sh.x*=sign
        ts=BODY_BONES['upperarm_'+side].translation;te=BODY_BONES['lowerarm_'+side].translation;th=BODY_BONES['hand_'+side].translation
        if x<.35:a,b,ta,tb=ss,se,ts,te
        else:a,b,ta,tb=se,sh,te,th
        t=max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared))
        q=(b-a).rotation_difference(tb-ta)
        sleeve=ta.lerp(tb,t)+q@(p-a.lerp(b,t))
        blend=max(0,min(1,(x-.145)/.07));blend=blend*blend*(3-2*blend)
        p=torso.lerp(sleeve,blend)
    else:p=torso
    w,near,normal,d=transfer(p)
    # Resolve body penetration while preserving intended loose clearance.
    signed=(p-near).dot(normal)
    if signed<.008 and d<.12:p+=normal*(.008-signed)
    coords.append(p);vweights.append(w)
faces=[tuple(p.vertices) for p in donor.data.polygons]
uvdata=donor.data.uv_layers.active.data
uvs=[[tuple(uvdata[i].uv) for i in p.loop_indices] for p in donor.data.polygons]
shirt=make_mesh('FieldSweaterMaster',coords,faces,vweights,uvs,materials=['Fabric'])
activate(shirt)
sub=shirt.modifiers.new('GarmentSurface','SUBSURF');sub.levels=1
bpy.ops.object.modifier_apply(modifier=sub.name)
# Add true inward cloth thickness and cuff/hem walls without a physics solver.
solid=shirt.modifiers.new('FabricThickness','SOLIDIFY');solid.thickness=.002;solid.offset=-1
bpy.ops.object.modifier_apply(modifier=solid.name)
master_coords=[v.co.copy() for v in shirt.data.vertices]
master_weights=[weights(shirt,v) for v in shirt.data.vertices]
master_faces=[tuple(p.vertices) for p in shirt.data.polygons]
master_uv=[[tuple(shirt.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in shirt.data.polygons]
bind(shirt,body_rig)
bpy.data.objects.remove(donor,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'FieldEquipment_Master.blend'))

for key,entry in INPUTS.items():
    if ONLY and key not in ONLY:continue
    rig,original=load(key);world=key=='Body';target=bone_world(rig)
    # Author every profile against its actual reference pose, including private
    # PKM and mirrored single-hand rigs; never rewrite a weapon's Skeleton.
    delta={n:target[n]@BODY_BONES[n].inverted() for n in BODY_BONES if n in target}
    converted=[];converted_w=[]
    for p,w in zip(master_coords,master_weights):
        valid={n:v for n,v in w.items() if n in delta};total=sum(valid.values())
        if total:
            converted.append(sum((delta[n]@p*v for n,v in valid.items()),Vector())/total)
            converted_w.append({n:v/total for n,v in valid.items()})
        else:
            converted.append(p.copy());converted_w.append({'pelvis':1})
    # Some left dual-wield components mirror a RIGHT-hand mesh at runtime.
    # Derive the actual skin side from geometry, never from the profile label.
    arm_mats=[i for i,m in enumerate(entry['materials']) if m['slot'].startswith('MI_Manny_')]
    arm_vertices={v for p in original.data.polygons if world or p.material_index in arm_mats for v in p.vertices}
    side_mass={side:sum(sum(w for n,w in weights(original,original.data.vertices[i]).items()
        if n.endswith('_'+side) and any(t in n for t in ('hand_','thumb_','index_','middle_','ring_','pinky_'))) for i in arm_vertices) for side in ('l','r')}
    sides=tuple(s for s in ('l','r') if side_mass[s]>max(side_mass.values())*.05)
    def sleeve_face(face):
        ws=[master_weights[i] for i in face]
        if world:return True
        avg=sum(arm_weight(w) for w in ws)/len(ws)
        if avg<.16:return False
        if len(sides)==1:
            return sum(sum(v for n,v in w.items() if n.endswith('_'+sides[0])) for w in ws)/len(ws)>.5
        return True
    chosen=[i for i,f in enumerate(master_faces) if sleeve_face(f)]
    used=sorted({v for i in chosen for v in master_faces[i]});remap={old:new for new,old in enumerate(used)}
    garment=make_mesh('Shirt_'+key,[converted[i] for i in used],
        [tuple(remap[v] for v in master_faces[i]) for i in chosen],[converted_w[i] for i in used],
        [master_uv[i] for i in chosen],materials=['Fabric'])
    if not world:
        bm=bmesh.new();bm.from_mesh(garment.data)
        bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(garment.data);bm.free()
    bind(garment,rig)

    original.data.calc_loop_triangles()
    source_arm_mats=[i for i,m in enumerate(entry['materials']) if m['slot'].startswith('MI_Manny_')]
    source_weights=[weights(original,v) for v in original.data.vertices]
    picked=[p for p in original.data.polygons if world or p.material_index in source_arm_mats]
    used=sorted({v for p in picked for v in p.vertices});mapping={v:i for i,v in enumerate(used)}
    base_coords=[original.matrix_world@original.data.vertices[i].co for i in used]
    base_weights=[source_weights[i] for i in used]
    base_faces=[tuple(mapping[v] for v in p.vertices) for p in picked]
    base_uv=[[tuple(original.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in picked]
    # Distinct sections support geometry replacement without scaling/hiding bones.
    # The original skin envelope stays underneath an unequipped region.
    materials=['SkinArms','SkinHands','SkinTorso','SkinRest']
    region=[]
    for p in picked:
        ws=[source_weights[i] for i in p.vertices]
        h=sum(hand_weight(w) for w in ws)/len(ws);a=sum(arm_weight(w) for w in ws)/len(ws)
        torso=sum(sum(v for n,v in w.items() if n.startswith(('spine','clavicle'))) for w in ws)/len(ws)
        region.append(1 if h>.55 else 0 if a>.30 else 2 if torso>.35 else 3)
    base=make_mesh('Base_'+key,base_coords,base_faces,base_weights,base_uv,region,materials)
    bind(base,rig)
    # A glove is a separate weighted shell, with its own material and actual cuff.
    glove_faces=[i for i,m in enumerate(region) if m==1]
    gi=sorted({v for i in glove_faces for v in base_faces[i]});gm={v:i for i,v in enumerate(gi)}
    gcoords=[]
    for i in gi:
        # Keep contact-side growth tiny; the outer shell carries the visible thickness.
        normal=base.data.vertices[i].normal
        gcoords.append(base_coords[i]+normal*.0007)
    glove=make_mesh('Gloves_'+key,gcoords,[tuple(gm[v] for v in base_faces[i]) for i in glove_faces],
        [base_weights[i] for i in gi],[base_uv[i] for i in glove_faces],materials=['Leather'])
    # Finish exposed wrist boundaries with short inward walls. This also covers
    # the skin/glove section boundary during wrist flexion.
    activate(glove)
    wall=glove.modifiers.new('LeatherThickness','SOLIDIFY');wall.thickness=.0014;wall.offset=-1
    bpy.ops.object.modifier_apply(modifier=wall.name)
    bind(glove,rig)
    for obj,kind in ((base,'Base'),(garment,'Shirt'),(glove,'Gloves')):
        export(obj,rig,f'SK_{key}_{kind}')
    # Preserve editable profile derivatives without the unrelated weapon geometry.
    bpy.data.objects.remove(original,do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(key+'_Equipment.blend')))
    REPORT[key]={'world':world,'source':entry['mesh'],'skeleton':entry['skeleton'],'sides':list(sides),
        'hide_source_materials':list(range(len(entry['materials']))) if world else source_arm_mats,
        'shirt_covers':[0,2] if world else [0,2,3], 'glove_covers':[1],
        'counts':{'base':len(base.data.polygons),'shirt':len(garment.data.polygons),'gloves':len(glove.data.polygons)}}
    print('AUTHORED_OUTFIT',key,REPORT[key]['counts'],flush=True)
(ROOT/'authored.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
