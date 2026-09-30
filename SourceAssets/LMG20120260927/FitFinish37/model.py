"""201 art-only seam/cover authoring. No renders, tests, or animation edits.
All dimensions are the existing game rig's local metres.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'Surface32/LMG201_S32_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST'
root=rig.data.bones['WPN_root'].matrix_local.copy()
records=json.loads((S/'Surface32/source.json').read_text())
parts={r['object']:bpy.data.objects[r['object']] for r in records}
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def mat(name,role):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(.01096,.01444,.01764,1);b.inputs['Roughness'].default_value=.60;b.inputs['Metallic'].default_value=0
 m['Finish37Role']=role;return m
coat=mat('M_LMG201_F37_Cover','Cover');inside=mat('M_LMG201_F37_Interior','Interior');steel=mat('M_LMG201_F37_Satin','Satin');receiver=mat('M_LMG201_F37_Receiver','Receiver')
def localize(ob):
 a=root.inverted()@ob.matrix_world;ns=[(a.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(a);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)
def bind(ob,bone):
 ns=[(root.to_3x3()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(root);ob.matrix_world=Matrix.Identity(4);ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 ob.data.normals_split_custom_set(ns)
 ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE');ob.modifiers.new('Native201Rig','ARMATURE').object=rig
def finish_normals(ob,bevel=0):
 select([ob])
 if bevel:
  m=ob.modifiers.new('Small manufactured edge radius','BEVEL');m.width=bevel;m.segments=3;m.limit_method='ANGLE';m.angle_limit=math.radians(35);m.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(42)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
 m=ob.modifiers.new('Planar corner normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=40;bpy.ops.object.modifier_apply(modifier=m.name)
def unwrap(ob):
 select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
def capture_normals(ob):
 me=ob.data
 return {tuple(p.vertices):(p.normal.copy(),{me.loops[i].vertex_index:me.corner_normals[i].vector.copy() for i in p.loop_indices}) for p in me.polygons}
def transport_normals(ob,original):
 me=ob.data;me.update();normals=[Vector((0,0,1)) for _ in me.loops]
 for p in me.polygons:
  old=original.get(tuple(p.vertices));rot=old[0].rotation_difference(p.normal) if old and old[0].length>.1 and p.normal.length>.1 else None
  for i in p.loop_indices:normals[i]=(rot@old[1][me.loops[i].vertex_index]).normalized() if rot else p.normal.copy()
 me.normals_split_custom_set(normals)
def mesh(name,vertices,faces,materials):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
 for m in materials:me.materials.append(m)
 ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);return ob

# Smooth, asymmetric upper silhouette. Both receiver opening and lid use these
# same art stations; the front hinge origin itself is retained unchanged.
ys=np.array([-.2379,-.2335,-.226,-.217,-.207,-.188,-.166,-.147,-.127,-.110,-.100,-.0967])
ls=np.array([-.0137,-.0145,-.0184,-.0213,-.0225,-.0240,-.0252,-.0260,-.0265,-.0265,-.0258,-.0255])
rs=np.array([.0105,.0130,.0240,.0294,.0320,.0320,.0310,.0300,.0292,.0283,.0276,.0270])
roof=np.array([.0710,.0720,.0736,.0790,.0844,.0852,.0856,.0856,.0853,.0836,.0815,.0810])
def lr(y):return float(np.interp(y,ys,ls)),float(np.interp(y,ys,rs))
def seam_z(y):
 # Original oblique split transformed by Install30, retained as the seat datum.
 return float(np.interp(y,[-.2375,-.22251,-.097],[.0605,.0621,.0728]))
def ztop(y):return float(np.interp(y,ys,roof))

rec=parts['Receiver'];localize(rec)
receiver_normals=capture_normals(rec)
old=np.load(S/'Surface32/Work/Receiver.npz');edited=np.load(S/'Detail35/Work/Receiver.npz')['vertices']
for vertex,p in zip(rec.data.vertices,edited):vertex.co=p
# Preserve every existing UV and original exterior corner normal. Only the new
# rim/interior receives new normals and its own physical UV projection.
me=rec.data;me.materials[0]=receiver;me.materials[1]=inside
v=np.array([x.co[:] for x in me.vertices]);f=np.array([p.vertices[:] for p in me.polygons]);mids=np.array([p.material_index for p in me.polygons]);p=v[f]
n=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-10);c=p.mean(1)
cap=(mids==1)&(c[:,1]>-.239)&(c[:,1]<-.095)&(c[:,2]>.057)&(n[:,2]>.7)
capfaces=f[cap];edge=np.sort(np.concatenate([capfaces[:,[0,1]],capfaces[:,[1,2]],capfaces[:,[2,0]]]),axis=1);unique,counts=np.unique(edge,axis=0,return_counts=True);boundary=unique[counts==1]
adj={}
for a,b in boundary:adj.setdefault(int(a),[]).append(int(b));adj.setdefault(int(b),[]).append(int(a))
loops=[];seen=set()
for start in adj:
 if start in seen:continue
 seq=[start];prev=-1;cur=start
 while True:
  seen.add(cur);choices=[x for x in adj[cur] if x!=prev];nxt=choices[0]
  if nxt==start:break
  seq.append(nxt);prev,cur=cur,nxt
 loops.append(seq)
main=max(loops,key=len)
# Take the real connected boundary, regularize only the seam's upper shoulder.
# The rest of the receiver, grip, and contact regions retain their source points.
bv=v[np.array(main)];left=[];right=[];stations=np.linspace(-.232,-.099,134)
for y in stations:
 near=bv[abs(bv[:,1]-y)<.003]
 left.append(float(near[:,0].min()) if len(near) else -.022)
 right.append(float(near[:,0].max()) if len(near) else .028)
for vert in me.vertices:
 x,y,z=vert.co
 if not -.234<=y<=-.097:continue
 lo=float(np.interp(y,stations,left));hi=float(np.interp(y,stations,right));tl,tr=lr(y)
 w=max(0,min(1,(z-(seam_z(y)-.011))/.011));w=w*w*(3-2*w)
 if hi-lo>.005:vert.co.x=x+(((x-lo)/(hi-lo))*(tr-tl)+tl-x)*w
me.update()
# Replace only top split caps with an actual open recess. New side walls follow
# the boundary itself and lead down to the visible tray; no box overlays.
bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table();removed=[bm.faces[i] for i in np.flatnonzero(cap)]
bmesh.ops.delete(bm,geom=removed,context='FACES_ONLY');bm.verts.ensure_lookup_table()
uv=bm.loops.layers.uv.active or bm.loops.layers.uv.new('UV0')
new_faces=[]
for seq in loops:
 if len(seq)<3:continue
 outer=[bm.verts[i] for i in seq];center=sum((x.co for x in outer),Vector())/len(outer)
 inner_ring=[];bottom=[]
 for q in outer:
  co=q.co.copy();direction=Vector((center.x-co.x,center.y-co.y,0));direction.normalize();co+=direction*.00125;co.z-=.00035
  inner_ring.append(bm.verts.new(co));low=co.copy();low.z=.048;bottom.append(bm.verts.new(low))
 for j in range(len(seq)):
  k=(j+1)%len(seq)
  for vs in [(outer[j],outer[k],inner_ring[k],inner_ring[j]),(inner_ring[j],inner_ring[k],bottom[k],bottom[j])]:
   face=bm.faces.new(vs);face.material_index=1;face.smooth=False;new_faces.append(face)
 try:
  floor=bm.faces.new(list(reversed(bottom)));floor.material_index=1;floor.smooth=False;new_faces.append(floor)
 except ValueError:pass
for face in new_faces:
 for loop in face.loops:loop[uv].uv=((loop.vert.co.x+.05)/.15,(loop.vert.co.y+.25)/.20)
bmesh.ops.recalc_face_normals(bm,faces=new_faces);bm.to_mesh(me);bm.free();me.update()
transport_normals(rec,receiver_normals)
rec['FitFinish37']='Shared upper shoulder boundary, removed former lid cut-cap, recessed side walls and tray; original exterior UV retained'

# Replace the old exterior shell, retaining authored inner detail islands.
with bpy.data.libraries.load(str(S/'Repair36/LMG201_R36_Lid.blend'),link=False) as (src,dst):dst.objects=['TopCover']
oldcover=dst.objects[0];bpy.context.scene.collection.objects.link(oldcover);localize(oldcover)
bm=bmesh.new();bm.from_mesh(oldcover.data);bm.verts.ensure_lookup_table();seen=set();islands=[]
for vert in bm.verts:
 if vert in seen:continue
 todo=[vert];found=set([vert]);seen.add(vert)
 while todo:
  a=todo.pop()
  for e in a.link_edges:
   b=e.other_vert(a)
   if b not in seen:seen.add(b);found.add(b);todo.append(b)
 islands.append(found)
external=max(islands,key=len)
bmesh.ops.delete(bm,geom=list(external),context='VERTS');bm.to_mesh(oldcover.data);bm.free()
# Internal detail fits the new cavity without changing longitudinal identities.
for q in oldcover.data.vertices:
 x,y,z=q.co;l,r=lr(y);center=(l+r)*.5;extent=(r-l)*.5-.0034
 q.co.x=center+(x-.0008)*min(1,extent/.0262)
oldcover.data.materials.clear()
cover_inside=mat('M_LMG201_F37_CoverInterior','CoverInterior')
cover_satin=mat('M_LMG201_F37_CoverSatin','CoverSatin')
for m in [coat,cover_inside,cover_satin]:oldcover.data.materials.append(m)
oldcover['FitFinish37']='Original D35/R36 visible internal forms, transverse fit to new cavity'

# Finite wall thickness and explicit flange. Rectangular ridge/recess language
# follows the selected source silhouette; radius is geometric, not noisy normals.
rows=np.unique(np.r_[ys,np.linspace(ys[0],ys[-1],95)])
verts=[];faces=[];mid=[]
for y in rows:
 l,r=lr(y);bottom=seam_z(y)+.0004;top=ztop(y);rad=.0017
 outer=[(l,bottom),(l,top-rad),(l+rad,top),(l+(r-l)*.28,top),(l+(r-l)*.30,top-.0013),(l+(r-l)*.69,top-.0013),(l+(r-l)*.71,top),(r-rad,top),(r,top-rad),(r,bottom)]
 inner_profile=[(x+(.0015 if i<3 else -.0015 if i>6 else 0),z-(.0015 if i not in [0,9] else 0)) for i,(x,z) in enumerate(outer)]
 verts.extend((x,y,z) for x,z in outer+inner_profile)
for j in range(len(rows)-1):
 for k in range(9):
  faces.append((20*j+k,20*(j+1)+k,20*(j+1)+k+1,20*j+k+1));mid.append(0)
  faces.append((20*j+10+k+1,20*(j+1)+10+k+1,20*(j+1)+10+k,20*j+10+k));mid.append(1)
 for k in [0,9]:faces.append((20*j+k,20*j+k+10,20*(j+1)+k+10,20*(j+1)+k));mid.append(1)
for j in [0,len(rows)-1]:
 for k in range(9):faces.append((20*j+k,20*j+k+1,20*j+k+11,20*j+k+10));mid.append(1)
lid=mesh('F37_FormedCoverShell',verts,faces,[coat,cover_inside])
for p,m in zip(lid.data.polygons,mid):p.material_index=m
finish_normals(lid,.00020)
select([oldcover,lid]);bpy.ops.object.join();lid=bpy.context.object;lid.name='TopCover_FitFinish37';unwrap(lid)
bpy.data.objects.remove(parts.pop('TopCover'),do_unlink=True);parts['TopCover_FitFinish37']=lid

# Bring the handguard's mounting end back to the common source mapping, fading
# outside the palm-contact region. All original UV loops/structural detail remain.
hg=parts['Handguard'];localize(hg)
hg_normals=capture_normals(hg)
zp=np.array([-.23,-.13276,-.07727,-.027,-.01,0,.071,.104,.13579,.1416,.15,.16,.174,.181616,.236625]);zq=np.array([-.124,-.07391,-.047,-.036,-.00644,.00165,.030,.04866,.0605,.0648,.0724,.0758,.082,.086,.12562])
for q in hg.data.vertices:
 x,y,z=q.co;t=max(0,min(1,(y+.264)/.037));t=t*t*(3-2*t);height=max(0,min(1,(z-.036)/.023));oldz=(z-.00164749)/(.07075720/.176754802)-.026629;common=float(np.interp(oldz,zp,zq));q.co.z=z+(common-z)*t*height
hg['FitFinish37']='Upper rear interface eased to receiver; palm-contact region untouched'
transport_normals(hg,hg_normals)

# Front newly authored metal: taper its existing rear collar into the retained
# tube end using the actual tube section, rather than a second covering collar.
front=parts['GasFrontHardware'];localize(front);tube=np.load(S/'Surface32/Work/GasTube.npz');tv=tube['vertices'];near=tv[(tv[:,1]<-.569)&(tv[:,1]>-.572)]
front_normals=capture_normals(front)
center=np.median(near[:,[0,2]],axis=0);theta=np.arctan2(near[:,2]-center[1],near[:,0]-center[0]);radius=np.linalg.norm(near[:,[0,2]]-center,axis=1)
bins=np.linspace(-math.pi,math.pi,65);radii=[]
for a,b in zip(bins[:-1],bins[1:]):
 rr=radius[(theta>=a)&(theta<b)];radii.append(float(np.quantile(rr,.8)) if len(rr) else float(np.median(radius)))
for q in front.data.vertices:
 x,y,z=q.co;t=max(0,min(1,(y+.579)/.0088));t=t*t*(3-2*t)
 if not t:continue
 a=math.atan2(z-center[1],x-center[0]);r=math.hypot(x-center[0],z-center[1]);target=float(np.interp(a,(bins[:-1]+bins[1:])*.5,radii));w=t*max(0,min(1,(r-.005)/.004));newr=r+(target-r)*w;q.co.x=center[0]+math.cos(a)*newr;q.co.z=center[1]+math.sin(a)*newr
front['FitFinish37']='Existing rear fitting reshaped into tube section; eyelet and front silhouette retained'
transport_normals(front,front_normals)

# Bind only authored game-rigid parts. Unchanged parts keep original transforms.
bind(rec,'WPN_root');bind(lid,'LMG201_Cover');bind(hg,'WPN_root');bind(front,'WPN_root')
# Front sight base uses the already authored D35 vertices, retaining its mount.
base=parts['FrontSightBase_Fitted'];localize(base)
for q,p in zip(base.data.vertices,np.load(S/'Detail35/Work/FrontSightBase_Fitted.npz')['vertices']):q.co=p
base.data.materials[0]=bpy.data.materials['M_LMG201_R30_Surface'];base.data.materials[1]=inside;bind(base,'WPN_root')

# Cover-only UV atlas is shared by its shell and internal fittings. Baking these
# production texture inputs is asset authoring, not an acceptance render.
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=16
select([lid]);bpy.context.scene.render.bake.use_selected_to_active=False;bpy.context.scene.render.bake.margin=12
maps={}
for label,bake in [('Normal','NORMAL'),('AO','AO')]:
 im=bpy.data.images.new('T_LMG201_F37_Cover_'+label,2048,2048,alpha=False);im.colorspace_settings.name='Non-Color'
 for m in lid.data.materials:
  node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;m.node_tree.nodes.active=node
 bpy.context.scene.render.bake.normal_space='TANGENT';bpy.ops.object.bake(type=bake)
 im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();maps[label]=im.filepath_raw

body=[o for k,o in parts.items() if k not in ['FrontSight_Fitted','RearSight']]
roles={}
for ob in body:
 for m in ob.data.materials:
  if m and m.get('Finish37Role'):roles[m.name]=m['Finish37Role']
# Joined export is a temporary copy; named editable parts remain in the blend.
copies=[]
for ob in body:
 cp=ob.copy();cp.data=ob.data.copy();bpy.context.scene.collection.objects.link(cp);copies.append(cp)
select(copies);bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_F37_BodyParts'
select([joined,rig]);fbx=O/'Exports/SK_LMG201_F37_BodyParts.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
slots=[m.name for m in joined.data.materials];bpy.data.objects.remove(joined,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_FitFinish37_Editable.blend'))
report={'status':'authored_and_exported','weapon_fbx':str(fbx),'material_slots':slots,'material_roles':roles,'cover_maps':maps,'seam_stations':{'y':ys.tolist(),'left':ls.tolist(),'right':rs.tolist(),'roof':roof.tolist()},'source':'R36 current plus Surface32 editable and Detail35 receiver vertices','retained':'native bones/animation/arms/magazine/cloth/controls/sights/muzzle interface','game_tested':False,'acceptance_rendered':False}
(O/'model.json').write_text(json.dumps(report,indent=2));print('F37_MODEL_SAVED',str(fbx),flush=True)
