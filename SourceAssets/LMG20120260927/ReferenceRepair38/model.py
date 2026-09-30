"""201 visual reference repair. Reference pixel contours, fixed rig interfaces.
No real mechanism design; hidden forms are only game-visible supporting surfaces.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
for d in ['Exports','Textures','Before']: (O/d).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'FitFinish37/LMG201_FitFinish37_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST';root=rig.data.bones['WPN_root'].matrix_local.copy()
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def material(role):
 m=bpy.data.materials.new('M_LMG201_R38_'+role);m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Base Color'].default_value=(.01096,.014444,.017642,1);bs.inputs['Roughness'].default_value=.60 if role=='Cover' else .70 if role=='Interior' else .50;bs.inputs['Metallic'].default_value=.65 if role=='Satin' else 0
 return m
coat=material('Cover');inside=material('Interior');satin=material('Satin')
def localize(ob):
 xf=root.inverted()@ob.matrix_world;normals=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(normals)
def bind(ob,bone):
 ns=[(root.to_3x3()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(root);ob.data.normals_split_custom_set(ns)
 ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1.,'REPLACE');ob.modifiers.new('Original201Rig','ARMATURE').object=rig
def shape(name,vs,fs,mat=coat,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob)
 finish(ob,bevel);return ob
def finish(ob,bevel=0):
 select([ob]);bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
 if bevel:
  mod=ob.modifiers.new('Bounded authored bevel','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(ob.data)
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(38)
 bm.to_mesh(ob.data);bm.free();ob.data.update()
 mod=ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=45;bpy.ops.object.modifier_apply(modifier=mod.name)
def loft(name,rows,mat=coat,bevel=0):
 n=len(rows[0][1]);vs=[(x,y,z) for y,profile in rows for x,z in profile];fs=[tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))]
 fs.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rows)-1) for i in range(n));return shape(name,vs,fs,mat,bevel)
def boolean(ob,cutter,operation):
 select([ob]);mod=ob.modifiers.new('Closed visual shell '+operation,'BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
def cylinder(name,c,r,length,axis='Y',mat=satin):
 vs=[];n=32;a,b,k={'X':(1,2,0),'Y':(0,2,1),'Z':(0,1,2)}[axis]
 for sign in [-1,1]:
  for i in range(n):
   p=list(c);p[k]+=sign*length/2;p[a]+=r*math.cos(i*math.tau/n);p[b]+=r*math.sin(i*math.tau/n);vs.append(p)
 fs=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return shape(name,vs,fs,mat,.00012)
def box(name,c,size,mat=coat,bevel=.0003):
 x,y,z=c;a,b,h=np.array(size)/2;profile=[(x-a,z-h),(x+a,z-h),(x+a,z+h),(x-a,z+h)];return loft(name,[(y-b,profile),(y+b,profile)],mat,bevel)

# Restore only the bad receiver to the pre-F37 exterior. Recess an inset region
# of the original cap while retaining the connected perimeter and source UVs.
old=bpy.data.objects['Receiver'];bpy.data.objects.remove(old,do_unlink=True)
with bpy.data.libraries.load(str(S/'Surface32/LMG201_S32_Editable.blend'),link=False) as (src,dst):dst.objects=['Receiver']
rec=dst.objects[0];bpy.context.scene.collection.objects.link(rec);localize(rec);me=rec.data
for q,p in zip(me.vertices,np.load(S/'Detail35/Work/Receiver.npz')['vertices']):q.co=p
me.update();me.materials[0]=bpy.data.materials['M_LMG201_F37_Receiver'];me.materials[1]=bpy.data.materials['M_LMG201_F37_Interior']
v=np.array([q.co[:] for q in me.vertices]);f=np.array([p.vertices[:] for p in me.polygons]);mid=np.array([p.material_index for p in me.polygons]);pts=v[f];norm=np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-10);c=pts.mean(1)
cap=(mid==1)&(c[:,1]>-.239)&(c[:,1]<-.095)&(c[:,2]>.057)&(norm[:,2]>.7)
# Remove the cap AND the generated internal fragments from the visible well.
# The bounded cutter stays inside the original exterior; its finite floor and
# side surfaces become the actual tray, rather than pulling a triangulated fan.
well=[]
for yy,ww in [(-.217,.013),(-.212,.017),(-.202,.022),(-.122,.022),(-.111,.017)]:
 well.append((yy,[(.0008-ww,.0495),(.0008+ww,.0495),(.0008+ww,.12),(.0008-ww,.12)]))
cut=loft('R38_VisibleTrayCut',well,bpy.data.materials['M_LMG201_F37_Interior'])
boolean(rec,cut,'DIFFERENCE');me=rec.data
ns=[n.vector.copy() for n in me.corner_normals]
for p in me.polygons:
 if p.material_index==1:
  for i in p.loop_indices:
   co=me.vertices[me.loops[i].vertex_index].co;me.uv_layers.active.data[i].uv=((co.x+.04)/.08,(co.y+.24)/.15);ns[i]=p.normal.copy()
me.normals_split_custom_set(ns);pinned=set()
rec['R38']='Restored source exterior; bounded visible well removes cap and internal remnants; no width extrapolation';bind(rec,'WPN_root')

# The side elevations follow User_Left's visible shoulder/top step changes.
# Width follows the existing receiver's art interface, not an arbitrary scale.
station_y=np.array([-.2375,-.232,-.223,-.218,-.185,-.179,-.144,-.140,-.106,-.097])
roof=np.array([.0665,.0725,.0838,.0850,.0850,.0825,.0825,.0868,.0868,.0795])
half=np.array([.025,.029,.033,.0345,.035,.035,.0345,.034,.032,.029])
cx=.0008
def roof_at(y):return float(np.interp(y,station_y,roof))
def seam(y):return float(np.interp(y,[-.2375,-.22251,-.097],[.0605,.0621,.0728]))
rows=[]
for y in station_y:
 w=float(np.interp(y,station_y,half));z=roof_at(y);lo=seam(y)+.0003;shoulder=min(.006,max(.002,(z-lo)*.5));inset=min(.007,w*.23)
 profile=[(cx-w,lo),(cx-w,z-shoulder),(cx-w+inset,z-.0005),(cx-w+inset+.002,z),(cx+w-inset-.002,z),(cx+w-inset,z-.0005),(cx+w,z-shoulder),(cx+w,lo)]
 rows.append((float(y),profile))
lid=loft('R38_ReferenceFormedCover',rows,coat)
# A single closed cavity subtraction gives the shell a continuous inner roof,
# side returns and end walls. No Solidify offset and no unmatched loft seams.
inner_rows=[]
for y in sorted(set([-.231,-.104]+[float(x) for x in station_y if -.231<x<-.104])):
 w=float(np.interp(y,station_y,half))-.0022;z=roof_at(y)-.0022;inset=min(.006,w*.24)
 inner_rows.append((y,[(cx-w,.042),(cx-w,z-.006),(cx-w+inset,z),(cx+w-inset,z),(cx+w,z-.006),(cx+w,.042)]))
cutter=loft('R38_InnerCavity',inner_rows,inside);boolean(lid,cutter,'DIFFERENCE');finish(lid,.00038)
lid.data.materials.append(inside)
for p in lid.data.polygons:
 if p.normal.z<-.2:p.material_index=1
parts=[lid]

# Source pixel tracings on Video26/Reference/lid_inside.png. Mapping is an art
# correspondence for the visible surface; occluded mechanical geometry is unknown.
def xy(px,py):return cx-(px-190)*(.064/270),-.103-(py-198)*(.129/520)
traces={
 'InnerStampedPlate':[(92,220),(107,209),(289,209),(303,222),(303,305),(287,324),(287,361),(273,381),(300,401),(300,430),(276,448),(276,514),(260,542),(111,542),(93,526)],
 'LowerStampedReturn':[(105,575),(117,563),(257,563),(277,584),(277,657),(264,676),(239,676),(234,656),(220,649),(203,649),(193,660),(171,660),(165,622),(153,619),(151,651),(125,651),(114,641),(109,612)],
 'UpperPressureCasting':[(188,238),(210,241),(222,249),(261,251),(271,264),(271,290),(250,307),(236,308),(229,344),(213,360),(193,356)],
 'SideLever':[(276,379),(297,379),(314,396),(313,446),(298,461),(278,460),(268,448),(268,418)],
 'GuideLeft':[(111,314),(123,309),(130,314),(130,518),(123,524),(111,518)],
 'GuideRight':[(246,331),(257,322),(267,327),(267,511),(260,522),(248,522)],
}
def trace_shape(name,pixels,depth,mat=inside,bevel=.00045):
 coords=[xy(x,y) for x,y in pixels];vs=[(x,y,.076) for x,y in coords]+[(x,y,.076-depth) for x,y in coords];n=len(coords);fs=[tuple(range(n-1,-1,-1)),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return shape('R38_'+name,vs,fs,mat,bevel)
for name,trace in traces.items():parts.append(trace_shape(name,trace,.002 if name in ['InnerStampedPlate','LowerStampedReturn'] else .006 if name=='UpperPressureCasting' else .004,coat if name=='UpperPressureCasting' else inside))
def point(px,py,down):
 x,y=xy(px,py);return (x,y,.076-down)
parts.append(cylinder('R38_LongVisibleRoller',point(185,415,.0066),.0042,.036,'Y'))
for py in [347,481]:parts.append(cylinder('R38_RollerCollar',point(185,py,.0066),.0048,.0018,'Y',coat))
parts.append(cylinder('R38_ShortVisibleRoller',point(128,272,.0060),.0036,.0138,'Y'))
for py in [246,294]:parts.append(cylinder('R38_ShortCollar',point(128,py,.0060),.0040,.0014,'Y',coat))
for py in [249,350]:parts.append(cylinder('R38_TransverseDetail',point(193,py,.0060),.0016,.036,'X'))
parts.append(cylinder('R38_LeverBoss',point(296,421,.0044),.0030,.0014,'Z'))
# Two curved rails belong to the stamped layer and terminate on visible feet.
for px in [119,257]:
 for py in [321,514]:parts.append(box('R38_GuideFoot',point(px,py,.0032),(.006,.0028,.002),coat,.00035))

# The rear latch in the closed reference has a thick border and ten horizontal
# ribs. Its rear surface sits on the formed shoulder, instead of replacing it.
latch=box('R38_RearThumbLatch',(cx,-.0998,.0797),(.023,.006,.0124),coat,.00085);parts.append(latch)
for z in np.linspace(.0748,.0846,10):parts.append(cylinder('R38_ThumbRib',(cx,-.09665,float(z)),.00037,.0195,'X',coat))
# Reference-visible hinge feet terminate in the retained original pivot zone.
for side in [-1,1]:parts.append(box('R38_VisibleHingeReturn',(cx+side*.012,-.2265,.0625),(.005,.012,.005),inside,.0006))
parts.append(cylinder('R38_VisibleHingeBar',(cx,-.2268,.0609),.0021,.027,'X',satin))

# Replace failed cover completely. Named source parts remain editable in a
# separate collection, with a joined rigged production mesh for export.
old=bpy.data.objects.get('TopCover_FitFinish37')
if old:bpy.data.objects.remove(old,do_unlink=True)
edit=bpy.data.collections.new('R38_EditableCoverFeatures');bpy.context.scene.collection.children.link(edit)
for ob in parts:
 cp=ob.copy();cp.data=ob.data.copy();edit.objects.link(cp);cp.hide_render=True;cp.hide_set(True)
select(parts);bpy.context.view_layer.objects.active=lid;bpy.ops.object.join();lid.name='TopCover_ReferenceRepair38'
select([lid]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
bind(lid,'LMG201_Cover')

# Targeted diagnosis requested by the user: record same-source bounds and actual
# welded shell boundary, so a bad seam cannot be handed off as a finished model.
diag={}
for ob in [rec,lid]:
 xf=root.inverted()@ob.matrix_world;v=np.array([(xf@q.co)[:] for q in ob.data.vertices]);me=ob.data;me.calc_loop_triangles();f=np.array([q.vertices[:] for q in me.loop_triangles]);ed=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);edges,n=np.unique(ed,axis=0,return_counts=True)
 diag[ob.name]={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'x_outliers_over_90mm':int((abs(v[:,0])>.09).sum()),'open_edges':int((n==1).sum()),'max_edge':float(np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1).max())}
 if diag[ob.name]['x_outliers_over_90mm']:raise RuntimeError('Lateral spike remains '+ob.name)
 if ob==lid and diag[ob.name]['open_edges']:raise RuntimeError('New cover has unclosed edges')
np.savez_compressed(O/'reference_traces.npz',**{k:np.array(v) for k,v in traces.items()})

# Bake only the newly UV-authored cover; the receiver retains its structural map.
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=16;select([lid]);bpy.context.scene.render.bake.use_selected_to_active=False;bpy.context.scene.render.bake.margin=12
maps={}
for label in ['Normal','AO']:
 im=bpy.data.images.new('T_LMG201_R38_Cover_'+label,2048,2048,alpha=False);im.colorspace_settings.name='Non-Color'
 for m in lid.data.materials:
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;m.node_tree.nodes.active=n
 bpy.context.scene.render.bake.normal_space='TANGENT';bpy.ops.object.bake(type='NORMAL' if label=='Normal' else 'AO');im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();maps[label]=im.filepath_raw
select([rec,lid,rig]);fbx=O/'Exports/SK_LMG201_R38_ReceiverCover.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_ReferenceRepair38.blend'))
(O/'model.json').write_text(json.dumps({'status':'authored_and_exported','fbx':str(fbx),'diagnosis':diag,'cap_faces':int(cap.sum()),'receiver_pinned_boundary_vertices':len(pinned),'maps':maps,'reference_images':['Surface32/References/User_Left.png','Surface32/References/User_Right.png','Video26/Reference/lid_inside.png','Video26/Reference/weapon_01.65.png'],'visible_inner_contours':traces,'game_tested':False},indent=2));print('R38_SOURCE_SAVED',json.dumps(diag),flush=True)
