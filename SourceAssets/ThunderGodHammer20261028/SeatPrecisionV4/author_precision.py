"""Thor seat V4: continuous swept rails, fitted backs, recessed screws, baked PBR."""
import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
for f in ['Export','Textures','Preview']:(P/f).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_factory']
factory=b.objects[0];bpy.context.collection.objects.link(factory);source=factory.data;source.calc_loop_triangles()
def inspect_zero_tangents(mesh):
 mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
 return [f.index for f in mesh.polygons if any(mesh.loops[i].tangent.length<1e-4 or mesh.loops[i].bitangent.length<1e-4 for i in f.loop_indices)]
# Existing microscopic cap slivers are retained with the factory surface.
# Import normals only; Unreal generates tangents from the final build mesh.
factory_tangent_faces=inspect_zero_tangents(source)
native_tri=len(source.loop_triangles);CX=-.0004452141001820564;CZ=.9095
bvh=BVHTree.FromPolygons([v.co for v in source.vertices],[list(t.vertices) for t in source.loop_triangles],all_triangles=True)
factory.hide_render=True;factory.hide_set(True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.bake.margin=16
scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=True
scene.render.use_compositing=False;scene.render.use_sequencer=False
def author_material(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links;ns.clear()
 bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs[0],out.inputs['Surface'])
 uv=ns.new('ShaderNodeUVMap');uv.uv_map='FlowUV'
 stretch=ns.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(18,280,1);ls.new(uv.outputs[0],stretch.inputs[0])
 noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1;noise.inputs['Detail'].default_value=2;ls.new(stretch.outputs[0],noise.inputs['Vector'])
 ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.94 for c in color),1);ramp.color_ramp.elements[1].color=(*color,1);ls.new(noise.outputs['Fac'],ramp.inputs[0]);ls.new(ramp.outputs[0],bs.inputs['Base Color'])
 bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 def mathnode(op,a=None,b=None):
  n=ns.new('ShaderNodeMath');n.operation=op
  for i,v in enumerate([a,b]):
   if v is None:continue
   if isinstance(v,(float,int)):n.inputs[i].default_value=v
   else:ls.new(v,n.inputs[i])
  return n.outputs[0]
 sep=ns.new('ShaderNodeSeparateXYZ');ls.new(uv.outputs[0],sep.inputs[0])
 # Two 0.04 mm engraved edge lines follow each rail's own longitudinal UV.
 grooves=[]
 for center in [.19,.81]:
  x=mathnode('DIVIDE',mathnode('SUBTRACT',sep.outputs['Y'],center),.014)
  grooves.append(mathnode('EXPONENT',mathnode('MULTIPLY',mathnode('MULTIPLY',x,x),-1.0)))
 height=mathnode('MULTIPLY',noise.outputs['Fac'],.000007)
 height=mathnode('ADD',height,mathnode('MULTIPLY',mathnode('ADD',*grooves),-.000040 if metal else -.000012))
 bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=1;bump.inputs['Distance'].default_value=1;ls.new(height,bump.inputs['Height']);ls.new(bump.outputs[0],bs.inputs['Normal'])
 return m
steel=author_material('AUTHOR_SatinForgedSteel',(.30,.325,.35),.94,.45)
dark=author_material('AUTHOR_OxidizedRecess',(.10,.12,.14),.88,.49)
bronze=author_material('AUTHOR_AntiqueBronze',(.34,.18,.065),.91,.44)
pad=author_material('AUTHOR_LeatherDamper',(.024,.027,.029),0,.72)
MATS=[steel,dark,bronze,pad]
parts=[];parts_bvh=[];metrics=[]
def host_height(x,z,sgn):
 hit=bvh.ray_cast(Vector((x,sgn*.20,z)),Vector((0,-sgn,0)),.4)[0]
 if hit is None:
  near=bvh.find_nearest(Vector((x,sgn*.04,z)))[0]
  return sgn*near.y
 return sgn*hit.y
def smooth(values,r=5):
 kernel=np.exp(-.5*(np.arange(-r,r+1)/max(r/2,1))**2);kernel/=kernel.sum()
 return np.convolve(np.pad(values,(r,r),mode='edge'),kernel,mode='valid')
def rounded_profile(width,depth):
 # CCW continuous rounded rectangle; five subdivisions on every quarter fillet.
 rad=min(width*.12,depth*.34,.00065);out=[]
 for x,y,start in [(width/2-rad,depth-rad,0),(-width/2+rad,depth-rad,90),(-width/2+rad,rad,180),(width/2-rad,rad,270)]:
  for i in range(6):
   a=math.radians(start+i*90/5);out.append((x+rad*math.cos(a),y+rad*math.sin(a)))
 return out
def curve(controls):
 points=[Vector((x,z)) for x,z in controls];out=[];closed=(points[0]-points[-1]).length<1e-8
 if closed:points=points[:-1]
 for i in range(len(points) if closed else len(points)-1):
  a,b=points[i],points[(i+1)%len(points)]
  if closed:t0=(b-points[(i-1)%len(points)])*.5;t1=(points[(i+2)%len(points)]-a)*.5
  else:t0=(b-points[max(0,i-1)])*.5 if i else b-a;t1=(points[min(i+2,len(points)-1)]-a)*.5 if i+2<len(points) else b-a
  count=max(6,int((b-a).length/.00075))
  for k in range(count):
   t=k/count;t2=t*t;t3=t2*t;out.append((2*t3-3*t2+1)*a+(t3-2*t2+t)*t0+(-2*t3+3*t2)*b+(t3-t2)*t1)
 out.append(points[0] if closed else points[-1]);return out
def make_mesh(name,verts,faces,flow,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(mat)
 uv=me.uv_layers.new(name='UVMap');fu=me.uv_layers.new(name='FlowUV')
 for f in me.polygons:
  f.use_smooth=True
  for li in f.loop_indices:
   co=flow[me.loops[li].vertex_index];uv.data[li].uv=co;fu.data[li].uv=co
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);bpy.context.view_layer.objects.active=o
 # Only terminal edges exceed 55 degrees; rounded profiles already carry the side fillets.
 mod=o.modifiers.new('Rounded end termination','BEVEL');mod.width=.00005 if name in ['Flush recessed hex fastener','Fitted tapered fastening foot'] else .00024;mod.segments=4;mod.limit_method='ANGLE';mod.angle_limit=math.radians(55);mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=2e-7);bm.to_mesh(o.data);bm.free();o.data.update()
 mod=o.modifiers.new('Continuous fillet normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=o.modifiers.new('Stable Mikk tangent triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 me=o.data;me.calc_loop_triangles();parts.append(o)
 parts_bvh.append(BVHTree.FromPolygons([v.co for v in me.vertices],[list(t.vertices) for t in me.loop_triangles],all_triangles=True))
 return o
def rail(name,controls,sgn,width=.006,depth=.003,mat=steel,dense=False,layer=0,connect=False):
 pts=[Vector(p) for p in controls] if dense else curve(controls);closed=(pts[0]-pts[-1]).length<1e-8
 if closed:pts=pts[:-1]
 n=len(pts)
 sides=[];raw=[];widths=[];dist=[0.]
 for i,p in enumerate(pts):
  tangent=(pts[(i+1)%n]-pts[(i-1)%n]).normalized() if closed else (pts[min(i+1,n-1)]-pts[max(i-1,0)]).normalized();side=Vector((-tangent.y,tangent.x));sides.append(side)
  u=i/(n-1);ramp=1 if closed else min(u/.09,(1-u)/.09,1.0);ramp=ramp*ramp*(3-2*ramp);w=width*(.78+.22*ramp);widths.append(w)
  raw.append(max(host_height(CX+p.x+side.x*s,p.y+side.y*s,sgn) for s,_ in rounded_profile(w,depth)))
  if i:dist.append(dist[-1]+(p-pts[i-1]).length)
 # Smooth the local upper envelope, not the individual scan samples. Keep the
 # visible front clear while allowing its back to bed slightly into the host.
 # A global clearance offset incorrectly lifted an entire curved rail away.
 raw=np.array(raw);param=np.array(dist)/max(dist[-1],1e-6)
 peak=np.array([max(raw[max(0,i-7):min(n,i+8)]) for i in range(n)])
 envelope=smooth(peak,10)+.00015
 envelope+=max(0,float(np.max(raw-envelope))-depth*.72)
 if connect:
  for index,end in [(0,0),(n-1,1)]:
   point=pts[index];hits=[]
   for tree in parts_bvh:
    h=tree.ray_cast(Vector((CX+point.x,sgn*.20,point.y)),Vector((0,-sgn,0)),.4)[0]
    if h is not None:hits.append(sgn*h.y)
   if hits:
    target=max(hits)-.00015-depth-layer;distance=param if end==0 else 1-param
    weight=np.clip(1-distance/.25,0,1);weight=weight*weight*(3-2*weight)
    envelope+=(target-envelope[index])*weight
 vs=[];flow=[];prof_count=24
 for i,p in enumerate(pts):
  for s,d in rounded_profile(widths[i],depth):
   x=CX+p.x+sides[i].x*s;z=p.y+sides[i].y*s
   back=envelope[i]+layer
   front=envelope[i]+depth+layer
   h=back+d
   vs.append((x,sgn*h,z));flow.append((dist[i]/.035,s/widths[i]+.5))
 faces=[] if closed else [tuple(range(prof_count-1,-1,-1)),tuple(range((n-1)*prof_count,n*prof_count))]
 for i in range(n if closed else n-1):
  for j in range(prof_count):faces.append((i*prof_count+j,i*prof_count+(j+1)%prof_count,((i+1)%n)*prof_count+(j+1)%prof_count,((i+1)%n)*prof_count+j))
 o=make_mesh(name,vs,faces,flow,mat)
 metrics.append(dict(part=name,samples=n,profile_vertices=prof_count,closed_back=True,depth_fit='smooth manufactured rail; discrete fitted standoffs; no deep infill plate'))
 return o
def front_surface(x,z,sgn):
 origin=Vector((CX+x,sgn*.20,z));direction=Vector((0,-sgn,0));hits=[]
 for tree in [bvh]+parts_bvh:
  hit,normal,_,_=tree.ray_cast(origin,direction,.4)
  if hit is not None:hits.append((sgn*hit.y,hit,normal))
 _,point,normal=max(hits,key=lambda x:x[0]);normal=normal.normalized()
 if normal.y*sgn<0:normal=-normal
 # Broad washer sits across local scan variations, bolt axis follows the supported face.
 normal=(normal*.3+Vector((0,sgn,0))*.7).normalized()
 return point,normal
def screw(x,z,sgn,r=.0027):
 center,axis=front_surface(x,z,sgn);X=Vector((1,0,0));X=(X-axis*X.dot(axis)).normalized();Y=axis.cross(X).normalized()
 # Actual fitted fastening foot: the back follows the factory's local contact
 # patch, the top meets this rail, so the visible screw never floats over a gap.
 support=[];support_uv=[];N=60;top_h=sgn*center.y-.00035
 for k in range(4):
  rr=r*(1.00 if k==0 else .84 if k in [1,2] else 1.02)
  for j in range(N):
   a=2*math.pi*j/N;xx=CX+x+rr*math.cos(a);zz=z+rr*math.sin(a);bottom=min(host_height(xx,zz,sgn)-.0002,top_h-.0004)
   h=bottom if k==0 else bottom*.85+top_h*.15 if k==1 else bottom*.15+top_h*.85 if k==2 else top_h
   support.append((xx,sgn*h,zz));support_uv.append((j/N,k/3))
 sf=[tuple(range(N-1,-1,-1)),tuple(range(3*N,4*N))]
 for k in range(3):
  for j in range(N):sf.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 make_mesh('Fitted tapered fastening foot',support,sf,support_uv,steel)
 # Real shoulder, countersunk head, hex-socket sidewall and floor; no painted screw mark.
 profile=[(r*.58,-.00055,'round'),(r*1.15,-.00015,'round'),(r*1.15,.00015,'round'),(r,.00065,'round'),(r*.92,.00094,'round'),(r*.42,.00094,'hex'),(r*.39,.00038,'hex'),(0,.00038,'round')]
 N=60;vs=[];flow=[]
 for radius,h,shape in profile:
  for j in range(N):
   a=2*math.pi*j/N;rr=radius
   if shape=='hex':rr=radius*math.cos(math.pi/6)/math.cos((a+math.pi/6)%(math.pi/3)-math.pi/6)
   v=center+X*(rr*math.cos(a))+Y*(rr*math.sin(a))+axis*h;vs.append(tuple(v));flow.append((a/(2*math.pi),rr/r))
 faces=[]
 for k in range(len(profile)-2):
  for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
 # One center vertex avoids 60 collapsed quads at the socket floor.
 vs=vs[:-N]+[tuple(center+axis*profile[-1][1])];flow=flow[:-N]+[(.5,0)];c=len(vs)-1
 for j in range(N):faces.append(((len(profile)-2)*N+j,(len(profile)-2)*N+(j+1)%N,c))
 faces.append(tuple(range(N-1,-1,-1)))
 return make_mesh('Flush recessed hex fastener',vs,faces,flow,steel)
def mirrored(p,sx):return [(sx*x,z) for x,z in p]
def arc(a,b,r):
 count=max(32,int(abs(b-a)*r*math.pi/180/.00065))
 # Factory medallion: approximately 105 mm wide by 82 mm high. Using a circle
 # pushed the upper and lower keepers into empty space outside the real rim.
 return [(r*math.cos(math.radians(a+(b-a)*i/count)),CZ+r*(.0412/.0535)*math.sin(math.radians(a+(b-a)*i/count))) for i in range(count+1)]
def bake_maps(ob,oid):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.hide_render=False;ob.select_set(True);bpy.context.view_layer.objects.active=ob
 me=ob.data;me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
 tangent_faces=inspect_zero_tangents(me)
 print('HARDWARE_TANGENT_FACES',oid,len(tangent_faces),flush=True)
 maps={}
 for kind in ['BaseColor','ORM','Normal']:
  name='T_ThorSeatV4_'+oid+'_'+kind;im=bpy.data.images.new(name,2048,2048,alpha=False);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  im.generated_color=(.5,.5,1,1) if kind=='Normal' else (0,0,0,1)
  for mat in me.materials:
   ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');out=next(n for n in ns if n.type=='OUTPUT_MATERIAL')
   target=ns.new('ShaderNodeTexImage');target.image=im;ns.active=target
   if kind=='Normal':ls.new(bs.outputs[0],out.inputs['Surface'])
   else:
    em=ns.new('ShaderNodeEmission')
    if kind=='BaseColor':ls.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
    else:em.inputs['Color'].default_value=(1,bs.inputs['Roughness'].default_value,bs.inputs['Metallic'].default_value,1)
    ls.new(em.outputs[0],out.inputs['Surface'])
  bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT');im.filepath_raw=str(P/'Textures'/(name+'.png'));im.file_format='PNG';im.save();maps[kind]=im
  print('BAKED',oid,kind,flush=True)
 # Preserve the exact editable shader source as a hidden authoring copy.
 author=ob.copy();author.data=ob.data.copy();author.name='AUTHOR_'+oid;bpy.context.collection.objects.link(author);author.hide_render=True;author.hide_set(True)
 mat=bpy.data.materials.new('M_ThorSeatV4_'+oid);mat.use_nodes=True;ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
 nodes={}
 for kind,im in maps.items():n=ns.new('ShaderNodeTexImage');n.image=im;nodes[kind]=n
 ls.new(nodes['BaseColor'].outputs[0],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['ORM'].outputs[0],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 nm=ns.new('ShaderNodeNormalMap');ls.new(nodes['Normal'].outputs[0],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
 me.materials.clear();me.materials.append(mat)
 for f in me.polygons:f.material_index=0
 return mat
styles=[('reinforced_block','厚壁重铸座'),('ribbed_light','镂肋轻型座'),('laminated_damper','叠片缓冲座'),('ancient_breaking_seal_seat','破势古印座'),('storm_drive_seat','鸣雷疾驱座')]
rows=[]
for oid,label in styles:
 parts=[];parts_bvh=[];metrics=[]
 for sign in [-1,1]:
  if oid=='reinforced_block':
   for sx in [-1,1]:
    for controls in [[(.030,.979),(.044,.976),(.052,.966),(.054,.949)],[(.053,.879),(.046,.865),(.030,.856)]]:
     rail('Swept forged shoulder',mirrored(controls,sx),sign,.0105,.0038,steel)
    for x,z in [(.041,.977),(.054,.951),(.044,.864)]:screw(sx*x,z,sign,.0025)
   for a,b in [(20,65),(115,160),(200,245),(295,340)]:rail('Fitted round medallion keeper',arc(a,b,.0535),sign,.0036,.0021,steel,True)
  elif oid=='ribbed_light':
   for sx in [-1,1]:
    rail('Continuous open outer rib',mirrored([(.032,.856),(.050,.873),(.057,.902),(.056,.930),(.047,.956),(.031,.978)],sx),sign,.0048,.0033,steel)
    for controls in [[(.031,.978),(.033,.959),(.046,.947),(.052,.944)],[(.032,.856),(.034,.869),(.046,.879),(.052,.881)]]:
     rail('Curved fork branch',mirrored(controls,sx),sign,.0039,.0027,steel,connect=True)
    for x,z in [(.031,.976),(.033,.858),(.056,.914)]:screw(sx*x,z,sign,.0022)
  elif oid=='laminated_damper':
   for sx in [-1,1]:
    for top in [True,False]:
     controls=[(.027,.978),(.040,.974),(.050,.963),(.053,.951)] if top else [(.027,.857),(.040,.863),(.049,.874),(.053,.886)]
     for layer in range(3):
      rail('Precision curved damping lamella',mirrored(controls,sx),sign,.0092-layer*.0005,.0016,steel,layer=layer*.0024)
      if layer<2:rail('Recessed compliant separator',mirrored(controls,sx),sign,.0074,.00075,pad,layer=.0017+layer*.0024)
     for x,z in [(.033,.976 if top else .860),(.051,.959 if top else .879)]:screw(sx*x,z,sign,.0025)
  elif oid=='ancient_breaking_seal_seat':
   for a,b in [(8,82),(98,172),(188,262),(278,352)]:rail('Machined antique circle segment',arc(a,b,.0538),sign,.0041,.0026,bronze,True)
   for sx in [-1,1]:
    for z in [.969,.861]:
     rail('Rounded ancient seal socket',mirrored([(.028,z),(.034,z+.0045),(.041,z),(.034,z-.0045),(.028,z)],sx),sign,.0026,.0020,bronze)
    for x,z in [(.053,CZ),(.0435,.9335),(.0435,.8855)]:screw(sx*x,z,sign,.0019)
  elif oid=='storm_drive_seat':
   for sx in [-1,1]:
    rail('Swept conductive crown arch',mirrored([(.025,.853),(.044,.866),(.056,.890),(.057,.919),(.048,.948),(.032,.974),(.011,.986)],sx),sign,.0064,.0036,bronze)
    rail('Tapered crown lightning tongue',mirrored([(.040,.965),(.030,.953),(.041,.955),(.036,.946)],sx),sign,.0020,.0018,steel)
    for x,z in [(.026,.854),(.054,.889),(.048,.948),(.014,.984)]:screw(sx*x,z,sign,.0022)
   for a,b in [(30,65),(115,150),(210,245),(295,330)]:rail('Recessed conductive keeper',arc(a,b,.0535),sign,.0032,.0020,bronze,True)
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();hardware=bpy.context.object;hardware.name='Hardware_'+oid
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 hardware.data.calc_loop_triangles();hardware_tri=len(hardware.data.loop_triangles)
 bake_maps(hardware,oid)
 base=bpy.data.objects.new('SM_ThunderGodHammer_head_mount_'+oid,source.copy());bpy.context.collection.objects.link(base)
 group=base.vertex_groups.new(name='FACTORY_UNCHANGED');group.add(list(range(len(base.data.vertices))),1,'REPLACE')
 bpy.ops.object.select_all(action='DESELECT');hardware.select_set(True);base.select_set(True);bpy.context.view_layer.objects.active=base;bpy.ops.object.join()
 me=base.data;me.calc_loop_triangles()
 assert all((me.vertices[i].co-v.co).length<1e-9 for i,v in enumerate(source.vertices))
 assert all((me.uv_layers[0].data[i].uv-v.uv).length<1e-8 for i,v in enumerate(source.uv_layers[0].data))
 error=max((me.corner_normals[i].vector-n.vector).length for i,n in enumerate(source.corner_normals));assert error<2e-5,error
 extra=[v.co for v in me.vertices[len(source.vertices):]]
 assert all(CX-.065<v.x<CX+.065 and v.z>.844 for v in extra),'Attachment crosses original mating planes'
 bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(base.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
 rows.append(dict(id=oid,name=label,mesh=base.name,triangles=len(me.loop_triangles),native_triangles=native_tri,hardware_triangles=hardware_tri,native_normal_error=error,materials=[m.name for m in me.materials],bounds_m=[[min(v.co[i] for v in me.vertices) for i in range(3)],[max(v.co[i] for v in me.vertices) for i in range(3)]],textures={k:f'Textures/T_ThorSeatV4_{oid}_{k}.png' for k in ['BaseColor','ORM','Normal']},rail_fit=metrics))
 base.hide_render=True;base.hide_set(True)
 (P/'model_manifest.json').write_text(json.dumps(dict(complete=False,parts=rows,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
 print('PRECISION_SEAT_COMPLETE',oid,len(me.loop_triangles),flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThorSeatsPrecisionV4.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(complete=True,parts=rows,factory_blender_zero_tangent_face_indices=factory_tangent_faces,normal_convention='OpenGL tangent space; UE texture flip_green_channel=True; UE recomputes Mikk tangents with full precision UVs',normal_source='Cycles baked material relief on authored curved geometry, longitudinal fine grooves and brushed grain; original factory normal is retained separately.',textures_per_seat=3,texture_resolution=2048,factory_source=str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_PRECISION_SEATS_EXPORTED',flush=True)
