"""Locally rebuild the cloth box crown around its existing rim and belt outlet."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST';root=rig.data.bones['WPN_root'].matrix_local.copy()
src=bpy.data.objects['AmmoBag'];ob=bpy.data.objects.new('C45_AmmoBag_Local',src.data.copy());bpy.context.scene.collection.objects.link(ob)
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for a in objects:a.hide_set(False);a.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
def rounded(theta,center,half,radius):
    d=Vector((math.cos(theta),math.sin(theta)));low=0.;high=max(half)*2
    for _ in range(28):
        r=(low+high)/2;q=Vector((abs(d.x*r)-half[0]+radius,abs(d.y*r)-half[1]+radius));distance=Vector((max(q.x,0),max(q.y,0))).length+min(max(q),0)-radius
        if distance>0:high=r
        else:low=r
    return Vector((center[0]+d.x*(low+high)/2,center[1]+d.y*(low+high)/2))
me=ob.data;normals=[n.vector.copy() for n in me.corner_normals];bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
nl=[bm.loops.layers.float.new('C45N'+x) for x in 'xyz'];fresh=bm.faces.layers.int.new('C45NewFace')
for f in bm.faces:
    for l,i in zip(f.loops,me.polygons[f.index].loop_indices):
        for k,layer in enumerate(nl):l[layer]=normals[i][k]
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
cut=-.030;bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-6 for v in e.verts)];adj={}
for e in edges:
    for v in e.verts:adj.setdefault(v,[]).append(e.other_vert(v))
if any(len(a)!=2 for a in adj.values()):raise RuntimeError('Non-simple cut boundary')
start=min(adj,key=lambda v:v.co.x);loop=[start];prev=None;cur=start
while True:
    nxt=next(v for v in adj[cur] if v!=prev)
    if nxt==start:break
    loop.append(nxt);prev,cur=cur,nxt
if len(loop)!=len(adj):raise RuntimeError('Multiple source rim loops')
area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))
if area<0:loop.reverse()
# The original perimeter owns the seam. The clean rings follow its accumulated
# arc rather than sorting disconnected points by angle or extrapolating widths.
n=len(loop);lengths=[(loop[(i+1)%n].co-loop[i].co).length for i in range(n)];total=sum(lengths);acc=[0.]
for a in lengths[:-1]:acc.append(acc[-1]+a)
center=(.005,-.13215);theta0=math.atan2(loop[0].co.y-center[1],loop[0].co.x-center[0]);thetas=[theta0+math.tau*a/total for a in acc]
outer=[rounded(t,center,(.0665,.03865),.006) for t in thetas]
inner=[rounded(t,(.042,-.1322),(.0158,.0362),.002) for t in thetas]
uvs=list(bm.loops.layers.uv.values());mask=bm.loops.layers.uv.new('C45Region');physical=bm.loops.layers.uv.new('C45FabricMeters')
source_uv={v:next(l[uvs[0]].uv.copy() for l in v.link_loops) for v in loop}
source_n={v:sum((Vector(tuple(l[a] for a in nl)) for l in v.link_loops),Vector()).normalized() for v in loop}
def face(vertices,stage,uvkind):
    f=bm.faces.new(vertices);f[fresh]=1;f.smooth=True
    for l in f.loops:
        p=l.vert.co;blend=smooth((p.z-cut)/.004) if uvkind=='side' else 1.;l[mask].uv=(blend,0)
        for k,layer in enumerate(nl):l[layer]=source_n[loop[index[l.vert]]][k]
        if uvkind=='side':
            i=index[l.vert];l[physical].uv=(acc[i],p.z)
        else:l[physical].uv=(p.x,p.y)
        l[uvs[0]].uv=source_uv[loop[index[l.vert]]]
        if len(uvs)>1:l[uvs[1]].uv=l[uvs[0]].uv
    return f
index={v:i for i,v in enumerate(loop)};previous=loop
for step in range(1,8):
    t=step/7;a=smooth(t);row=[]
    for i,v in enumerate(loop):
        xy=Vector(v.co[:2]).lerp(outer[i],a);p=Vector((xy.x,xy.y,cut+.0075*t));w=bm.verts.new(p);index[w]=i;row.append(w)
    for i in range(n):face([previous[i],previous[(i+1)%n],row[(i+1)%n],row[i]],t,'side')
    previous=row
# Continuous cloth roof with restrained broad tension folds. The hole is formed
# by this annulus and its return wall, not hidden by a separate overlay block.
for step in range(1,15):
    t=step/14;row=[]
    for i in range(n):
        xy=outer[i].lerp(inner[i],t);fold=.00045*math.sin(math.pi*t)*math.sin(82*xy.x+37*xy.y)*smooth((.02-xy.x)/.05)
        binding=.00055*math.exp(-((t-.07)/.055)**2)
        w=bm.verts.new((xy.x,xy.y,-.0225+.0015*math.sin(math.pi*t)+fold+binding));index[w]=i;row.append(w)
    for i in range(n):face([previous[i],previous[(i+1)%n],row[(i+1)%n],row[i]],1.,'roof')
    previous=row
for z in [-.025,-.033,-.041]:
    row=[]
    for i,xy in enumerate(inner):w=bm.verts.new((xy.x,xy.y,z));index[w]=i;row.append(w)
    for i in range(n):face([previous[i],previous[(i+1)%n],row[(i+1)%n],row[i]],1.,'roof')
    previous=row
f=bm.faces.new(list(reversed(previous)));f[fresh]=1
for l in f.loops:l[mask].uv=(1,0);l[physical].uv=l.vert.co.xy
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(me);bm.free();me.update()
stored=[me.attributes['C45N'+x].data for x in 'xyz'];fresh=me.attributes['C45NewFace'].data;custom=[]
for p in me.polygons:
    p.use_smooth=True
    for li in p.loop_indices:
        v=me.vertices[me.loops[li].vertex_index];old=Vector(tuple(a[li].value for a in stored))
        if not fresh[p.index].value:normal=old.normalized() if old.length else v.normal
        else:normal=old.normalized().lerp(v.normal,smooth((v.co.z-cut)/.004)).normalized() if old.length and cut<=v.co.z<=cut+.004 else v.normal
        custom.append(normal)
me.normals_split_custom_set(custom)

# A bounded reinforced outlet frame follows the measured first belt segment.
hardware=[]
mount=bpy.data.materials.new('C45_Mount');mount.diffuse_color=(.023,.028,.026,1);mount.use_nodes=True
bs=next(x for x in mount.node_tree.nodes if x.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.023,.028,.026,1);bs.inputs['Roughness'].default_value=.49
def objmesh(name,verts,faces,material):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();m.materials.append(material);a=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(a);return a
count=96;vs=[];fs=[]
profiles=[((.0198,.0393),.0042,-.024),((.0198,.0393),.0042,-.0063),((.0183,.0378),.0027,-.004822),((.0158,.0362),.002,-.004822),((.0158,.0362),.002,-.024)]
for half,r,z in profiles:
    for i in range(count):p=rounded(math.tau*i/count,(.042,-.1322),half,r);vs.append((p.x,p.y,z))
for k in range(len(profiles)):
    for i in range(count):j=(i+1)%count;l=(k+1)%len(profiles);fs.append((k*count+i,k*count+j,l*count+j,l*count+i))
frame=objmesh('C45_OutletFrame',vs,fs,mount);hardware.append(frame)
def block(name,position,size,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=position);a=bpy.context.object;a.name=name;a.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);a.data.materials.append(mount);mod=a.modifiers.new('Small physical edge radius','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name);hardware.append(a)
block('C45_ReceiverLatch',(.003,-.107,-.014),(.023,.016,.018356),.0011)
block('C45_FrontKeeper',(.003,-.153,-.020),(.021,.007,.006),.00085)
for a in hardware:
    select([a]);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(a.data);bm.free()
    for p in a.data.polygons:p.use_smooth=True
    a.data.set_sharp_from_angle(angle=math.radians(38));select([a]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
select(hardware);bpy.ops.object.join();mountob=bpy.context.object;mountob.name='C45_Mount_Local'
objects=[];roles={}
for prefix,bone in [('Old','LMG201_Box'),('New','New_LMG201_Box')]:
    for source,role in [(ob,'Cloth'),(mountob,'C45Mount')]:
        a=source.copy();a.data=source.data.copy();bpy.context.scene.collection.objects.link(a);a.name='C45_'+prefix+'Box_'+role
        material=source.data.materials[0].copy();material.name='M_LMG201_Cloth33__'+prefix+'Box_'+role;a.data.materials.clear();a.data.materials.append(material)
        for p in a.data.polygons:p.material_index=0
        roles[material.name]='Cloth' if role=='Cloth' else 'Mount'
        ns=[root.to_3x3()@x.vector for x in a.data.corner_normals];a.data.transform(root);a.data.normals_split_custom_set(ns);a.parent=rig;a.matrix_parent_inverse=Matrix.Identity(4);a.matrix_basis=Matrix.Identity(4);a.vertex_groups.clear();a.vertex_groups.new(name=bone).add(list(range(len(a.data.vertices))),1.,'REPLACE');a.modifiers.new('ExistingBoxRig','ARMATURE').object=rig;objects.append(a)
select(objects+[rig]);fbx=O/'Exports/SK_LMG201_C45_Boxes.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
for a in objects:a.hide_set(True);a.hide_render=True
report={'fbx':str(fbx),'roles':roles,'source':'Install30/LMG201_R30_NativeFit.blend','cut_z_m':cut,'seam_vertices':n,'local_objects':[ob.name,mountob.name],'cloth_triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'mount_triangles':sum(len(p.vertices)-2 for p in mountob.data.polygons),'material_mask_uv':2,'fabric_uv':3,'upper_height_m':-.004822,'bone_contract':['LMG201_Box','New_LMG201_Box'],'animation_modified':False}
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_ClothTop45.blend'));(O/'model.json').write_text(json.dumps(report,indent=2));print('C45_MODEL_SAVED',json.dumps(report),flush=True)
