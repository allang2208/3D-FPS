"""Fit game optic saddles to the current M16 handle; preserve optical bodies."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;C=json.loads((O/'capture.json').read_text());W=O/'Working';X=O/'Exports';X.mkdir(exist_ok=True)
h=np.load(W/'host.npz');hp=h['p'];ht=h['t'];tree=BVHTree.FromPolygons(hp.tolist(),ht.tolist())
keys=['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','thermal_scope']
result={'assets':{},'complete':False,'frame':'Existing M16 optic local metres; +X forward; component transform unchanged'}
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def make(name,vs,fs):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def extrude(name,profile,x0,x1):
 n=len(profile);vs=[(x,y,z) for x in (x0,x1) for y,z in profile];fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return make(name,vs,fs)
def finish(o):
 active(o);b=o.modifiers.new('Small machined edge radius','BEVEL');b.width=.00012;b.segments=2
 bpy.ops.object.modifier_apply(modifier=b.name)
 for f in o.data.polygons:f.use_smooth=True
 o.data.set_sharp_from_angle(angle=math.radians(38))
 n=o.modifiers.new('Planar weighted normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=35;bpy.ops.object.modifier_apply(modifier=n.name)
def cylinder(name,loc,radius,depth,vertices=48):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);finish(o);return o
def foot(x,y):
 hit=tree.ray_cast(Vector((x,y,.012)),Vector((0,0,-1)),.06)[0]
 if hit is None and -.007<x<.017:
  # Bridge the real through-hole between two measured support points. Do not
  # let a ray through the drilled opening pull the saddle down into the handle.
  left=tree.ray_cast(Vector((-.010,y,.012)),Vector((0,0,-1)),.06)[0]
  right=tree.ray_cast(Vector((.020,y,.012)),Vector((0,0,-1)),.06)[0]
  if left is not None and right is not None:return left.z+(right.z-left.z)*(x+.010)/.030-.00004
 if hit is None:raise RuntimeError('No handle support at '+str((x,y)))
 return hit.z-.00004
def mount(key):
 vs=[];fs=[];sections=49
 for x in np.linspace(-.060,.063,sections):
  # One continuous inverted-U saddle with an open central sight channel.
  profile=[(-.0059,foot(x,-.0059)),(-.0083,foot(x,-.0083)),(-.0083,-.0054),(-.0086,-.0054),(-.0086,-.0034),(.0086,-.0034),(.0086,-.0054),(.0083,-.0054),(.0083,foot(x,.0083)),(.0059,foot(x,.0059)),(.0059,-.0092),(-.0059,-.0092)]
  vs.extend((x,y,z) for y,z in profile)
 n=12;fs.extend([tuple(range(n-1,-1,-1)),tuple(range((sections-1)*n,sections*n))])
 for i in range(sections-1):fs.extend((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for j in range(n))
 core=make('Contoured carry handle saddle',vs,fs)
 top={'holographic':.00189,'panoramic_red_dot':.00246,'prism_scope_2x':.00121,'lpvo_1_6x':.00121,'eoth_holographic':-.00002,'thermal_scope':-.00004}[key]
 if key=='eoth_holographic':
  # Source clamp cavity: roof at 1.374 mm, shoulder void at -1.133..-0.213 mm.
  # Body lowered 1.35 mm; this profile seats inside its existing clamp jaws.
  half=[(.0083,top),(.0093,-.00016),(.0100,-.00116),(.0103,-.00161),(.0103,-.00243),(.0086,-.0034),(.0086,-.0056)]
 elif key=='holographic':
  half=[(.0083,top),(.0093,.00144),(.0103,.00074),(.0103,-.0010),(.0086,-.0034),(.0086,-.0056)]
 elif key=='thermal_scope':
  half=[(.0083,top),(.0093,top),(.0103,-.0010),(.0103,-.0020),(.0086,-.0034),(.0086,-.0056)]
 else:
  # Narrow crown meets the source clamp's upper recess; side wings stay below
  # the lower jaws. This retains the authored body and its hard-coded aim point.
  half=[(.0083,top),(.0085,top-.00010),(.0089,-.00010),(.0103,-.00018),(.0103,-.0020),(.0086,-.0034),(.0086,-.0056)]
 profile=[(-y,z) for y,z in reversed(half)]+half
 # Put the transverse gap at the optic's central recoil bar, not a tooth.
 for center in np.arange(-.060,.061,.010):
  c=center+.005
  x0=max(-.0635,c-.002385);x1=min(.0635,c+.002385)
  if x1<=x0:continue
  tooth=extrude('Dovetail rail segment',profile,x0,x1)
  active(core);b=core.modifiers.new('Connected rail segment','BOOLEAN');b.operation='UNION';b.solver='EXACT';b.object=tooth;bpy.ops.object.modifier_apply(modifier=b.name);bpy.data.objects.remove(tooth,do_unlink=True)
 finish(core)
 # Small mechanical pieces overlap their bearing surfaces; they do not hide
 # the saddle/receiver seam. Preserve the existing measured through-hole axis.
 # The handle underside is curved. A shaped bearing washer contacts that
 # surface; a flat nut alone would leave the old 3 mm hanging hardware gap.
 wv=[];wf=[];count=64
 for j in range(count):
  a=j*math.tau/count;dx,dy=math.cos(a),math.sin(a)
  hit=tree.ray_cast(Vector((.005+.0081*dx,.0081*dy,-.040)),Vector((0,0,1)),.025)[0]
  if hit is None:raise RuntimeError('Washer lacks measured bearing surface')
  z=hit.z+.00004
  wv.extend([(.005+.0025*dx,.0025*dy,-.0283),(.005+.0081*dx,.0081*dy,-.0283),(.005+.0081*dx,.0081*dy,z),(.005+.0025*dx,.0025*dy,z)])
 for j in range(count):
  for k in range(4):wf.append((j*4+k,((j+1)%count)*4+k,((j+1)%count)*4+(k+1)%4,j*4+(k+1)%4))
 washer=make('Contoured underside bearing washer',wv,wf);finish(washer)
 parts=[core,washer,cylinder('Captive mounting stud',(.005,0,-.018),.0023,.023),cylinder('Under-handle locking nut',(.005,0,-.0305),.0081,.0045,64)]
 for j in range(24):
  a=j*math.tau/24;parts.append(cylinder('Thumb nut knurl',(.005+.00795*math.cos(a),.00795*math.sin(a),-.0305),.00042,.0031,6))
 return parts,top
for key in keys:
 bpy.ops.wm.open_mainfile(filepath=str(W/(key+'.blend')),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 o=bpy.data.objects[key];row=C['assets'][key];me=o.data
 for other in list(bpy.context.scene.objects):
  if other!=o:bpy.data.objects.remove(other,do_unlink=True)
 if key=='thermal_scope':keep=[f for f in me.polygons if not(f.material_index==0 and max(me.vertices[v].co.z for v in f.vertices)<.000001)];interface=0
 else:
  interface=next(i for i,s in enumerate(row['slots']) if s['name'] in ('M16_InterfaceMetal','Universal_InterfaceSteel'))
  keep=[f for f in me.polygons if f.material_index!=interface]
 shift=Vector((-.027,0,-.00135)) if key=='eoth_holographic' else Vector((0,0,0))
 used=sorted({v for f in keep for v in f.vertices});lookup={v:i for i,v in enumerate(used)}
 vs=[tuple(me.vertices[v].co+shift) for v in used];fs=[tuple(lookup[v] for v in f.vertices) for f in keep];mids=[f.material_index for f in keep]
 nl=len(me.uv_layers);uvs=[[tuple(layer.data[li].uv) for f in keep for li in f.loop_indices] for layer in me.uv_layers];norms=[tuple(me.corner_normals[li].vector) for f in keep for li in f.loop_indices]
 body_faces=len(fs);parts,top=mount(key)
 for part in parts:
  pm=part.data;off=len(vs);vs.extend(tuple(v.co) for v in pm.vertices);fs.extend(tuple(off+v for v in f.vertices) for f in pm.polygons);mids.extend([interface]*len(pm.polygons));norms.extend(tuple(n.vector) for n in pm.corner_normals)
  for f in pm.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(f.normal[k]))]
   for li in f.loop_indices:
    p=pm.vertices[pm.loops[li].vertex_index].co;value=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    for layer in uvs:layer.append(value)
 combined=bpy.data.meshes.new('Measured M16 optic assembly');combined.from_pydata(vs,[],fs);combined.update()
 for mat in me.materials:combined.materials.append(mat)
 for f,mid in zip(combined.polygons,mids):f.material_index=mid;f.use_smooth=True
 for i,values in enumerate(uvs):
  layer=combined.uv_layers.new(name='UV'+str(i))
  for loop,value in zip(layer.data,values):loop.uv=value
 combined.normals_split_custom_set(norms);o.data=combined
 for part in parts:bpy.data.objects.remove(part,do_unlink=True)
 active(o);fbx=X/('SM_M16_'+key+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE')
 bpy.ops.wm.save_as_mainfile(filepath=str(X/(key+'_Editable.blend')))
 sockets=json.loads(json.dumps(row['sockets']))
 if key=='eoth_holographic':
  for s in sockets.values():s['location']=[s['location'][0]+shift.x*100,s['location'][1]-shift.y*100,s['location'][2]+shift.z*100]
 result['assets'][key]={'fbx':str(fbx),'shift_m':list(shift),'sockets':sockets,'body_faces_retained':body_faces,'adapter_faces':len(fs)-body_faces,'rail_crown_m':top,'uv_channels':nl,'host_contact_overlap_mm':.04}
 (O/'production.json').write_text(json.dumps(result,indent=2));print('M16_OPTIC_AUTHORED',key,result['assets'][key],flush=True)
result['complete']=True;(O/'production.json').write_text(json.dumps(result,indent=2))
