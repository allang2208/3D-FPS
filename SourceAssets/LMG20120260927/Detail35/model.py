"""Historical source dependency: do not run this D35 installer recipe directly.
Repair36/rebuild_lid.py reads the pre-export prefix and replaces the failed
even-offset thickness operation. The original D35 lid outputs are retired.
Refine the installed art parts in place; no extra runtime overlay components.
Coordinates below are proportions in the existing game rig, not fabrication data.
"""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;(O/'Exports').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Surface32/LMG201_S32_Editable.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST';root=rig.data.bones['WPN_root'].matrix_local.copy();cx=.0008
records=json.loads((O.parent/'Surface32/source.json').read_text());parts={r['object']:bpy.data.objects[r['object']] for r in records};newparts=[]
roles={};report={'source':'Surface32, installed ClothFeed33 body untouched outside replacement sections','operations':[]}
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def material(role,color,metal,rough):
 name='M_LMG201_D35_'+role;m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if bs is None:bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
 out=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
 m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;bs.inputs['Specular IOR Level'].default_value=.28;roles[name]=role;return m
coat=material('Coat',(.021,.026,.031),.35,.58);inner=material('Interior',(.015,.019,.023),.42,.64);satin=material('Satin',(.040,.046,.052),.78,.42);sight=material('Sight',(.014,.017,.020),.2,.68)
receiver_mat=bpy.data.materials['M_LMG201_R30_Surface'].copy();receiver_mat.name='M_LMG201_D35_Receiver';roles[receiver_mat.name]='Receiver'
for node in receiver_mat.node_tree.nodes:
 if node.type!='TEX_IMAGE' or not node.image:continue
 for kind in ['BaseColor','ORM','Normal']:
  path=O/'Textures'/('T_LMG201_D35_Receiver_'+kind+'.png')
  if kind in node.image.name and path.exists():
   node.image=bpy.data.images.load(str(path),check_existing=True);node.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';node.image.pack()
def localize(ob):
 transform=root.inverted()@ob.matrix_world;normals=[(transform.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(transform);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(normals);return ob
def normals(ob,angle=45):
 me=ob.data;select([ob]);bpy.ops.mesh.customdata_custom_splitnormals_clear()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for edge in bm.edges:edge.smooth=len(edge.link_faces)==2 and edge.calc_face_angle(0)<math.radians(angle)
 for face in bm.faces:face.smooth=True
 bm.to_mesh(me);bm.free();me.update()
 mod=ob.modifiers.new('Controlled planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
 bpy.ops.object.modifier_apply(modifier=mod.name)
def bevel(ob,width=.00025,segments=4):
 select([ob]);mod=ob.modifiers.new('Authored edge radius','BEVEL');mod.width=width;mod.segments=segments;mod.limit_method='ANGLE';mod.angle_limit=math.radians(40);mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 normals(ob)
def unwrap(ob):
 select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
def mesh(name,vs,fs,mat=coat,radius=.0003,bone='LMG201_Cover'):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);ob['bind_bone']=bone;newparts.append(ob)
 if radius:bevel(ob,radius)
 else:normals(ob)
 unwrap(ob);return ob
def sweep(name,rows,mat=coat,radius=.0003,bone='LMG201_Cover'):
 n=len(rows[0][1]);vs=[(cx+x,y,z) for y,p in rows for x,z in p];fs=[tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))];fs.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rows)-1) for i in range(n));return mesh(name,vs,fs,mat,radius,bone)
def box(name,c,size,mat=coat,radius=.0003,bone='LMG201_Cover'):
 x,y,z=c;a,b,h=[v*.5 for v in size];pr=[(x-cx-a,z-h),(x-cx+a,z-h),(x-cx+a,z+h),(x-cx-a,z+h)];return sweep(name,[(y-b,pr),(y+b,pr)],mat,radius,bone)
def cylinder(name,c,r,length,axis='X',mat=satin,radius=.00016,bone='LMG201_Cover',segments=64):
 a,b,k={'X':(1,2,0),'Y':(0,2,1),'Z':(0,1,2)}[axis];vs=[]
 for sign in [-1,1]:
  for i in range(segments):
   p=list(c);p[k]+=sign*length/2;p[a]+=r*math.cos(i*math.tau/segments);p[b]+=r*math.sin(i*math.tau/segments);vs.append(p)
 fs=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))];fs.extend((i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments));return mesh(name,vs,fs,mat,radius,bone)
def join_into(target,objects):
 if not objects:return
 for ob in objects:
  if ob in newparts:newparts.remove(ob)
 select(objects+[target]);bpy.ops.object.join()
def bind(ob,bone):
 norms=[root.to_3x3()@n.vector for n in ob.data.corner_normals];ob.data.transform(root);ob.data.normals_split_custom_set(norms);ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1.,'REPLACE');ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.modifiers.new('Native201Rig','ARMATURE').object=rig
# Local fairing retains the exterior seam coordinates and existing UVs.
for name in ['Receiver','TopCover','FrontSightBase_Fitted']:
 ob=localize(parts[name]);v=np.load(O/'Work'/(name+'.npz'))['vertices']
 for vert,co in zip(ob.data.vertices,v):vert.co=co
 for i,mat in enumerate(list(ob.data.materials)):
  ob.data.materials[i]=inner if 'Interior' in mat.name else receiver_mat if name=='Receiver' else coat
 normals(ob,48)
 report['operations'].append(name+': bounded original surface fairing and coherent planar normals')
# Remove the old broad cut-cap from the existing cover object, then give the
# retained outer skin a real inward wall and closed rim. No cap is overlaid.
cover=parts['TopCover'];bm=bmesh.new();bm.from_mesh(cover.data);caps=[f for f in bm.faces if f.material_index==1]
bmesh.ops.delete(bm,geom=caps,context='FACES');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cover.data);bm.free()
select([cover]);bpy.ops.mesh.customdata_custom_splitnormals_clear();sol=cover.modifiers.new('Continuous formed inner wall','SOLIDIFY');sol.thickness=.0018;sol.offset=-1;sol.use_even_offset=True;sol.use_quality_normals=True;sol.material_offset=1;sol.material_offset_rim=1;bpy.ops.object.modifier_apply(modifier=sol.name);normals(cover,48)
# Video-visible internal forms, all incorporated into this same moving lid.
details=[]
plate=[(-.020,.071),(.019,.071),(.023,.073),(.023,.075),(-.023,.075),(-.023,.073)]
details.append(sweep('D35_InnerSteppedPlate',[(-.209,plate),(-.115,plate)],inner,.00045))
for side in [-1,1]:
 details.append(box('D35_InnerSideReturn',(cx+side*.024,-.163,.0675),(.0026,.092,.0062),inner,.00055))
 for y in [-.199,-.121]:details.append(box('D35_InnerGuideFoot',(cx+side*.017,y,.0670),(.008,.004,.0032),coat,.0004))
 details.append(box('D35_InnerGuide',(cx+side*.017,-.159,.0685),(.0025,.071,.004),coat,.00045))
 details.append(box('D35_HingeReturn',(cx+side*.010,-.220,.064),(.003,.014,.0055),inner,.0004))
details.append(box('D35_UpperPressureForm',(cx+.006,-.125,.065),(.020,.024,.0086),coat,.0012))
details.append(cylinder('D35_UpperContactRoller',(cx-.010,-.126,.064),.0034,.019,'Y',satin,.00025))
details.append(cylinder('D35_LongContactRoller',(cx-.002,-.164,.064),.0044,.028,'Y',satin,.00025))
for y in [-.179,-.149]:details.append(cylinder('D35_RollerCollar',(cx-.002,y,.064),.0051,.0023,'Y',coat,.0002))
for y in [-.137,-.114]:details.append(cylinder('D35_TransversePin',(cx,y,.062),.0019,.038,'X',satin,.00012))
details.append(box('D35_InnerSideLever',(cx+.020,-.153,.064),(.006,.026,.0048),coat,.00075))
details.append(cylinder('D35_LeverPivot',(cx+.020,-.151,.0608),.0031,.0016,'Z',satin,.00015))
for x,y in [(-.015,-.12),(-.016,-.196),(.019,-.182)]:details.append(cylinder('D35_InnerRivet',(cx+x,y,.065),.0025,.0017,'Z',satin,.0002))
join_into(cover,details);bind(cover,'LMG201_Cover')
report['operations'].append('TopCover: old flat cut cap removed; connected thickness/rim and video-visible stepped plate, guides, pressure forms, collars, pins and rollers')
# Precision topology replaces the noisy head within each original sight object.
# Existing folding origins and the .11362 sight-line elevation remain fixed.
def replace_head(name,items,hinge):
 target=parts[name];old=target.data;select(items);bpy.ops.object.join();new=bpy.context.object
 target.data=new.data.copy();bpy.data.objects.remove(new,do_unlink=True);target.parent=None;target.modifiers.clear();target.matrix_world=root@Matrix.Translation(Vector(hinge));target.data.transform(Matrix.Translation(-Vector(hinge)))
 if old.users==0:bpy.data.meshes.remove(old)
fy=-.54212;fh=.0648;fz=.11362;front=[]
for side in [-1,1]:
 pr=[(side*.0048-.0013,fh),(side*.0048+.0013,fh),(side*.0039+.0011,fz-.008),(side*.0039-.0011,fz-.008)]
 front.append(sweep('D35_FrontStem',[(fy-.0033,pr),(fy+.0033,pr)],coat,.0004,'WPN_root'))
front.append(box('D35_FrontLowerFoot',(cx,fy,fh+.004),(.012,.008,.008),coat,.0006,'WPN_root'))
front.append(box('D35_FrontPostBed',(cx,fy,fz-.0095),(.009,.007,.004),coat,.00035,'WPN_root'))
vs=[];n=96
for y in [fy-.0019,fy+.0019]:
 for inner_ring in [False,True]:
  for i in range(n):
   a=i*math.tau/n;vs.append((cx+(.0100-.0016*inner_ring)*math.cos(a),y,fz+.0019+(.0101-.0016*inner_ring)*math.sin(a)))
fs=[]
for i in range(n):
 j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
front.append(mesh('D35_FrontGuard',vs,fs,coat,.00020,'WPN_root'))
post=[(-.0010,fz-.0075),(.0010,fz-.0075),(.00045,fz),(-.00045,fz)]
front.append(sweep('D35_FrontPost',[(fy-.0015,post),(fy+.0015,post)],sight,.00008,'WPN_root'))
replace_head('FrontSight_Fitted',front,(cx,fy,fh))
ry=.04252;rh=.0855;rz=.11362;rear=[]
rear.append(box('D35_RearFoldingFoot',(cx,ry,rh+.004),(.015,.014,.008),coat,.00065,'WPN_root'))
rear.append(cylinder('D35_RearAdjuster',(cx,ry,rz-.0083),.0036,.021,'X',satin,.0003,'WPN_root'))
pr=[(-.0078,rz-.010),(.0078,rz-.010),(.0078,rz+.0048),(.0058,rz+.0058),(.0046,rz+.005),(.0032,rz+.001),(.0011,rz+.001),(.0011,rz),(-.0011,rz),(-.0011,rz+.001),(-.0032,rz+.001),(-.0046,rz+.005),(-.0058,rz+.0058),(-.0078,rz+.0048)]
rear.append(sweep('D35_RearNotch',[(ry-.0032,pr),(ry+.0032,pr)],sight,.00018,'WPN_root'))
for side in [-1,1]:
 x=side*.0102;pr=[(x-.0016,rh+.004),(x+.0016,rh+.004),(x+.0016,rz+.0058),(x+.0006,rz+.008),(x-.0006,rz+.008),(x-.0016,rz+.0058)]
 rear.append(sweep('D35_RearWing',[(ry-.0060,pr),(ry+.0038,pr)],coat,.00055,'WPN_root'))
 rear.append(cylinder('D35_RearDial',(cx+side*.0113,ry,rz-.0083),.0041,.0024,'X',coat,.00025,'WPN_root'))
replace_head('RearSight',rear,(cx,ry,rh))
report['operations'].append('Front/rear heads: precision loops, open stem window, central post/U-notch, protective wings and transverse adjuster; original objects and folding origins')
bind(parts['Receiver'],'WPN_root');bind(parts['FrontSightBase_Fitted'],'WPN_root')
# Keep every unrelated source component exactly as saved in Surface32.
exports={}
def export(file,objects,skeletal=False):
 select(objects);bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'} if skeletal else {'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
for key,name in [('FrontSight','FrontSight_Fitted'),('RearSight','RearSight')]:
 ob=parts[name];saved=ob.matrix_world.copy();ob.matrix_world=Matrix.Identity(4);path=O/'Exports'/('SM_LMG201_D35_'+key+'.fbx');export(path,[ob]);exports[key]=str(path);ob.matrix_world=saved
body=[ob for name,ob in parts.items() if name not in ['FrontSight_Fitted','RearSight']];copies=[]
for ob in body:
 cp=ob.copy();cp.data=ob.data.copy();bpy.context.scene.collection.objects.link(cp);copies.append(cp)
select(copies);bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_D35_OriginalParts'
path=O/'Exports/SK_LMG201_D35_Weapon.fbx';export(path,[joined,rig],True);exports['Weapon']=str(path);bpy.data.objects.remove(joined,do_unlink=True)
report.update(exports=exports,material_roles=roles,sight_line_z=fz,rendered=False,tested=False,new_runtime_components=0)
(O/'model.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_D35_Editable.blend'));print('DETAIL35_MODEL_SAVED',json.dumps(exports),flush=True)
