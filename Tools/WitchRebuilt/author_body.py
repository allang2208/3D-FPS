"""Whole anatomical skin + original Witch identity, on the intact Foundation rig.
Offline authoring only. No render or gameplay validation is performed.
"""
import bpy, bmesh, json, math,sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import garment_polish

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
OLD=ROOT.parent/'WitchMeshy20260919'
FOUND=ROOT.parent/'WitchFoundation20260920'
OUT=ROOT/'Authoring'; DEL=ROOT/'Delivery'
OUT.mkdir(parents=True,exist_ok=True); DEL.mkdir(exist_ok=True)

def rest(r): return {b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
def weights(o,v): return {o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7}
def assign(o,values):
    o.vertex_groups.clear()
    for name in sorted({n for ws in values for n in ws}):o.vertex_groups.new(name=name)
    for i,ws in enumerate(values):
        ws=dict(sorted(ws.items(),key=lambda x:-x[1])[:8]); total=sum(ws.values())
        for n,w in ws.items():
            if w>1e-7:o.vertex_groups[n].add([i],w/total,'REPLACE')
def bind(o,r):
    o.parent=None; o.matrix_world=Matrix.Identity(4)
    o.modifiers.clear(); m=o.modifiers.new('FoundationSkin','ARMATURE');m.object=r
    o.parent=r;o.matrix_parent_inverse=r.matrix_world.inverted()
def material(o,name):
    old=o.data.materials[0] if o.data.materials else bpy.data.materials.new(name)
    mat=old.copy();mat.name=name;o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.material_index=0

bpy.ops.wm.open_mainfile(filepath=str(OLD/'Authoring/CleanRobeV06/Witch_CleanRobeV06.blend'))
oldrig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE'); sr=rest(oldrig)
parts={n:bpy.data.objects[n] for n in ('Witch_Hat','Witch_Head_Hair','Witch_UpperRobe','Witch_OriginalRobe_Render')}
for o in list(bpy.context.scene.objects):
    if o!=oldrig and o not in parts.values():bpy.data.objects.remove(o,do_unlink=True)
oldrig.animation_data_clear()
for b in oldrig.pose.bones:b.matrix_basis=Matrix.Identity(4)
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(FOUND/'Sources/Quinn.fbx'),use_anim=False)
rig=next(o for o in set(bpy.data.objects)-before if o.type=='ARMATURE')
for o in set(bpy.data.objects)-before:
    if o!=rig:bpy.data.objects.remove(o,do_unlink=True)
tr=rest(rig);rig.animation_data_clear()
target_bind_frame=rig.matrix_world.copy()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(OLD/'Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'),use_anim=False)
donor=next(o for o in set(bpy.data.objects)-before if o.type=='ARMATURE'); dr=rest(donor)
body=max((o for o in set(bpy.data.objects)-before if o.type=='MESH'),key=lambda o:len(o.data.vertices))
# Donor face morphs are irrelevant to this neck-down material subset. Their Basis
# still contains the source centimetre coordinates and would override the fit.
body.shape_key_clear()
# Keep the entire anatomical body material, including complete hands and feet.
# The source head is replaced at the designed neck boundary, never at limb heights.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=3],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(body.data);bm.free()
bodymat=body.data.materials[3].copy();bodymat.name='WitchRebuilt_AnatomicalSkin'
body.data.materials.clear();body.data.materials.append(bodymat)
for p in body.data.polygons:p.material_index=0
remap={}
for b in donor.data.bones:
    p=b
    while p and p.name not in tr:p=p.parent
    remap[b.name]=p.name if p else 'pelvis'
delta={n:tr[t]@dr[t].inverted() for n,t in remap.items()}
bodyweights=[];mw=body.matrix_world.copy()
for v in body.data.vertices:
    ws=weights(body,v); total=sum(ws.values()); p=mw@v.co
    v.co=sum((delta[n]@p*w/total for n,w in ws.items()),Vector())
    nw={}
    for n,w in ws.items():nw[remap[n]]=nw.get(remap[n],0)+w
    bodyweights.append(nw)
assign(body,bodyweights);bind(body,rig);body.name='WitchRebuilt_CompleteBody'
for o in set(bpy.data.objects)-before:
    if o!=body:bpy.data.objects.remove(o,do_unlink=True)

# Tailored inner fabric follows the intact skin weights. It covers the torso,
# forearms and shins behind the distressed outer robe; hands/feet/neck stay skin.
lining=body.copy();lining.data=body.data.copy();lining.name='WitchRebuilt_Lining';bpy.context.collection.objects.link(lining)
covered=[]
for v in body.data.vertices:
    skin_end=sum(w for n,w in bodyweights[v.index].items() if n.startswith(('hand_','foot_','ball_','index','middle','ring','pinky','thumb','neck_','head')))
    covered.append(skin_end<.5 and v.co.z>.15)
bm=bmesh.new();bm.from_mesh(lining.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if not all(covered[v.index] for v in f.verts)],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
for v in bm.verts:v.co+=v.normal*.0025
bm.to_mesh(lining.data);bm.free();lining.data.update();bind(lining,rig)
lm=bpy.data.materials.new('WitchRebuilt_Lining');lm.use_nodes=True
lbs=lm.node_tree.nodes.get('Principled BSDF');lbs.inputs['Base Color'].default_value=(.035,.026,.016,1);lbs.inputs['Roughness'].default_value=.88
lining.data.materials.clear();lining.data.materials.append(lm)
for p in lining.data.polygons:p.material_index=0;p.use_smooth=True

# Reference-axis fitting, using segment directions rather than incompatible bone rolls.
forward=sr['headfront'].translation-sr['Head'].translation;forward.z=0
rot=Matrix.Rotation(math.atan2(-1,0)-math.atan2(forward.y,forward.x),4,'Z')
mapping={'Hips':'pelvis','Spine02':'spine_01','Spine01':'spine_03','Spine':'spine_05',
         'neck':'neck_01','Head':'head','head_end':'head','headfront':'head'}
for prefix,s in (('Left','l'),('Right','r')):
    mapping.update({prefix+a:b+'_'+s for a,b in [('Shoulder','clavicle'),('Arm','upperarm'),('ForeArm','lowerarm'),('Hand','hand'),('UpLeg','thigh'),('Leg','calf'),('Foot','foot'),('ToeBase','ball')]})
child={'LeftArm':'LeftForeArm','LeftForeArm':'LeftHand','RightArm':'RightForeArm','RightForeArm':'RightHand'}
fits={}
for n,t in mapping.items():
    q=rot.to_3x3();scale=Matrix.Identity(3)
    if n in child:
        a=rot.to_3x3()@(sr[child[n]].translation-sr[n].translation)
        b=tr[mapping[child[n]]].translation-tr[t].translation
        q=a.rotation_difference(b).to_matrix()@q
        # Scale along this anatomical segment only; no pelvis/head bone-length ratios.
        axis=(sr[child[n]].translation-sr[n].translation).normalized()
        factor=b.length/a.length
        scale=Matrix.Identity(3)+Matrix([[axis[i]*axis[j]*(factor-1) for j in range(3)] for i in range(3)])
    fits[n]=(q@scale,sr[n].translation,tr[t].translation)
seam=parts['Witch_OriginalRobe_Render']
oldwaist=max((seam.matrix_world@v.co).z for v in seam.data.vertices)
newwaist=tr['pelvis'].translation.z
def robe_point(p):
    p=rot@p
    p.z=.075+(p.z/max(.01,oldwaist))*(newwaist-.075)
    return p

garment_report={}
for n,o in parts.items():
    oldcoords=[o.matrix_world@v.co for v in o.data.vertices]
    for v,p in zip(o.data.vertices,oldcoords):
        if n=='Witch_OriginalRobe_Render':v.co=robe_point(p)
        elif n in ('Witch_Hat','Witch_Head_Hair'):
            v.co=rot.to_3x3()@(p-sr['Head'].translation)+tr['head'].translation
        else:
            ws={k:w for k,w in weights(o,v).items() if k in fits and 'Leg' not in k and 'Foot' not in k and 'Toe' not in k}
            if not ws:ws={'Hips':1}
            total=sum(ws.values())
            fitted=sum(((fits[k][0]@(p-fits[k][1])+fits[k][2])*w/total for k,w in ws.items()),Vector())
            # Sewn waist uses the exact same rest mapping as the separate skirt.
            a=max(0,min(1,(p.z-oldwaist-.01)/.15));a=a*a*(3-2*a)
            v.co=robe_point(p).lerp(fitted,a)
    bind(o,rig)
    material(o,'WitchRebuilt_'+('Hat' if n=='Witch_Hat' else 'Head' if n=='Witch_Head_Hair' else 'UpperRobe' if n=='Witch_UpperRobe' else 'LowerRobe'))
    if 'Robe' in n:
        garment_report[n]=garment_polish.clean(o)
        garment_polish.fabric_material(o,'WitchRebuilt_UpperRobe' if n=='Witch_UpperRobe' else 'WitchRebuilt_LowerRobe',OLD/'Meshy/body/downloads')

# Barycentric weight transfer from the adapted anatomical body, with garment semantics.
body.data.calc_loop_triangles()
triangles=[tuple(t.vertices) for t in body.data.loop_triangles]
points=[v.co.copy() for v in body.data.vertices]
bvh=BVHTree.FromPolygons(points,triangles,all_triangles=True)
def transfer(p):
    hit,_,idx,_=bvh.find_nearest(p)
    ids=triangles[idx];a,b,c=[points[i] for i in ids]
    e0=b-a;e1=c-a;e2=hit-a;d00=e0.dot(e0);d01=e0.dot(e1);d11=e1.dot(e1)
    den=max(1e-12,d00*d11-d01*d01)
    v=(d11*e2.dot(e0)-d01*e2.dot(e1))/den;w=(d00*e2.dot(e1)-d01*e2.dot(e0))/den
    result={}
    for i,f in zip(ids,(1-v-w,v,w)):
        for name,weight in bodyweights[i].items():
            if name.startswith(('thigh','calf','foot','ball','ik_')):continue
            if name.startswith(('index','middle','ring','pinky','thumb')):name='hand_'+name[-1]
            result[name]=result.get(name,0)+max(0,f)*weight
    return result or {'pelvis':1}
for n,o in parts.items():
    if n=='Witch_Hat':ws=[{'head':1} for v in o.data.vertices]
    elif n=='Witch_Head_Hair':
        ws=[]
        for v in o.data.vertices:
            a=max(0,min(1,(v.co.z-(tr['neck_01'].translation.z-.01))/.10))
            ws.append({'head':a,'neck_01':1-a})
    elif n=='Witch_OriginalRobe_Render':ws=[{'pelvis':1} for v in o.data.vertices]
    else:
        ws=garment_polish.smooth_weights(o,[garment_polish.sleeve_weights(v.co,tr,transfer) for v in o.data.vertices])
    assign(o,ws)

# A low-resolution, continuous waist-to-hem drape. Only the waist is anchored.
skirt=parts['Witch_OriginalRobe_Render'];verts=[];faces=[];N=48;R=25;radii=[]
# Radial envelope preserves the source silhouette and avoids fitting the robe to legs.
raw=[v.co.copy() for v in skirt.data.vertices]
for j in range(R):
    t=j/(R-1);z=newwaist*(1-t)+.085*t
    for i in range(N):
        a=2*math.pi*i/N;d=Vector((math.cos(a),math.sin(a),0))
        nearby=[p for p in raw if abs(p.z-z)<.045 and p.xy.length>0.001 and d.dot(Vector((p.x,p.y,0)).normalized())>math.cos(.15)]
        # Keep a broad bell shape if a ragged source sector has no surface samples.
        radius=max([p.xy.length for p in nearby] or [.22+.15*t])
        radii.append(radius)
# A smooth simulation envelope must not inherit individual torn surface spikes.
for _ in range(5):
    prev=radii[:]
    for j in range(R):
        for i in range(N):radii[j*N+i]=.5*prev[j*N+i]+.25*(prev[j*N+(i-1)%N]+prev[j*N+(i+1)%N])
for _ in range(2):
    prev=radii[:]
    for j in range(1,R-1):
        for i in range(N):radii[j*N+i]=.5*prev[j*N+i]+.25*(prev[(j-1)*N+i]+prev[(j+1)*N+i])
for j in range(R):
    t=j/(R-1);z=newwaist*(1-t)+.085*t
    for i in range(N):
        a=2*math.pi*i/N;radius=radii[j*N+i];verts.append((math.cos(a)*radius,math.sin(a)*radius,z))
for j in range(R-1):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;c=b+N;d=a+N
        faces.extend(((a,c,b),(a,d,c)))
me=bpy.data.meshes.new('WitchRebuilt_DrapeProxy');me.from_pydata(verts,[],faces);me.update()
proxy=bpy.data.objects.new('WitchRebuilt_SimulationProxy',me);bpy.context.collection.objects.link(proxy)
proxy.data.materials.append(bpy.data.materials.new('WitchRebuilt_SimulationProxy'))
assign(proxy,[{'pelvis':1} for _ in verts]);bind(proxy,rig)
bpy.data.objects.remove(oldrig,do_unlink=True);rig.name='root'
# FBX armature import uses centimetre bones under a 0.01 object conversion.
# Keep that conversion through object removal, modifier baking and both exports.
# Mesh coordinates above are already in metres: never multiply them by 100 again.
rig.matrix_world=target_bind_frame
for o in [body,lining,*parts.values(),proxy]:
    o.matrix_parent_inverse=target_bind_frame.inverted();o.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for o in bpy.context.scene.objects:
    o.hide_set(False);o.hide_render=False
rig.data.pose_position='REST';bpy.context.scene.render.fps=30
# Preserve the full fitted anatomy as an editable source, while the runtime skin
# omits only the faces covered by the sewn inner fabric (no coplanar skin flicker).
bpy.data.libraries.write(str(OUT/'WitchRebuilt_AnatomySource.blend'),{body,rig})
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(covered[v.index] for v in f.verts)],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(body.data);bm.free();body.data.update()
# Keep the production refinement when rebuilding from the original anatomy.
import sys
sys.path.insert(0,str(Path(__file__).parent))
import refine_surface
refine_surface.apply(rig)
import author_drape04
author_drape04.apply(rig)
def export(name,include_proxy=False):
    rig.matrix_world=target_bind_frame
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o==rig or (o.type=='MESH' and ('SimulationProxy' not in o.name or include_proxy)):
            o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(DEL/name),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True)
export('SK_WitchRebuilt.fbx');export('SK_WitchRebuilt_ClothBuildSource.fbx',True)
rig.matrix_world=target_bind_frame
for o in bpy.context.scene.objects:
    if 'SimulationProxy' in o.name:o.hide_render=True;o.hide_set(True)
rig.data.pose_position='POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WitchRebuilt_Master.blend'))
(OUT/'body_manifest.json').write_text(json.dumps({'status':'authored, untested','body_source':str(OLD/'Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'),
 'body_scope':'Full fitted anatomy preserved in WitchRebuilt_AnatomySource.blend; runtime omits skin faces covered by inner fabric, preserving exposed hands/feet/neck',
 'skeleton_source':str(FOUND/'Sources/Quinn.fbx'),'armature_bind_frame':[list(row) for row in target_bind_frame],
 'robe_horizontal_expansion':1.0,'garment_cleanup':garment_report,
 'garment_weight_method':'Torso surface transfer, continuous arm-chain sleeve weights with adjacency smoothing; no third-party addon executed',
 'lower_robe':'Refinement03: continuous pelvis/thigh/calf support and rest clearance; no foot/toe weights; independent constrained drape',
 'render_parts':[body.name,lining.name,*parts.keys()],'proxy_vertices':len(verts),'proxy_faces':len(faces),
 'source_license':'Existing locally licensed Fab Zombie Female and Epic Quinn assets; original Witch Meshy sources. Do not redistribute raw library assets.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('AUTHORED WitchRebuilt body, clothing and separate simulation source',flush=True)
