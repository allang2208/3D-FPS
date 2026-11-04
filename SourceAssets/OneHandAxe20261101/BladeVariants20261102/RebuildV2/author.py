"""Clean manufactured heads with the stock mating end; no deformed donor blade."""

if __name__=='__main__':
    raise RuntimeError('R2 blade shapes were rejected. Current production is CrescentReferenceR4_20261104 and ContinuousBladesR5_20261104; this file only supplies reused helpers.')
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import *
KIND=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'SwiftCrescent'
PLANS={
 'SwiftCrescent':('axe_swift_crescent','轻型钩月斧刃',.007,.012),
 'HeavyCleaver':('axe_heavy_cleaver','厚背重劈斧刃',.012,.024),
 'FoldedArc':('axe_folded_arc','百炼弧锋斧刃',.009,.016)}
ID,LABEL,T,W=PLANS[KIND];CY=.0006362
for d in ['Export','Textures','Review','IconInputs','Icons','Before']:(P/d).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parents[1]/'ModulesV1/TacticalHatchet_Modules_Editable.blend'))
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory']
for o in bpy.context.scene.objects:o.hide_render=True;o.hide_set(True)

def cubic(a,b,c,d,n=18):
 a,b,c,d=map(Vector,(a,b,c,d))
 return [tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d) for t in [i/n for i in range(1,n+1)]]

def contour():
 # Counter-clockwise outline in X/Z, with explicitly designated cutting edge.
 pts=[(-.010,.180),(-.010,.238)]
 def curve(b,c,d,n=18):pts.extend(cubic(pts[-1],b,c,d,n))
 if KIND=='SwiftCrescent':
  curve((-.010,.251),(-.021,.260),(-.032,.269));pts.extend([(-.034,.294),(-.018,.300)])
  curve((.030,.292),(.091,.294),(.150,.313))
  start=len(pts)-1
  curve((.170,.268),(.144,.214),(.101,.182),40);end=len(pts)-1
  curve((.102,.221),(.083,.245),(.058,.247));curve((.035,.249),(.023,.232),(.023,.211));pts.append((.023,.180))
 elif KIND=='HeavyCleaver':
  curve((-.010,.251),(-.032,.263),(-.044,.264));pts.extend([(-.044,.303),(-.029,.310),(.168,.315)])
  start=len(pts)-1
  curve((.195,.276),(.174,.212),(.124,.172),42);end=len(pts)-1
  curve((.103,.196),(.080,.223),(.054,.230));curve((.033,.237),(.023,.225),(.023,.206));pts.append((.023,.180))
 else:
  curve((-.010,.255),(-.028,.262),(-.036,.270));pts.extend([(-.035,.296),(-.019,.302)])
  curve((.041,.290),(.101,.304),(.159,.315))
  start=len(pts)-1
  curve((.186,.270),(.154,.207),(.106,.176),42);end=len(pts)-1
  curve((.107,.212),(.087,.240),(.059,.245));curve((.035,.251),(.023,.229),(.023,.208));pts.append((.023,.180))
 return pts,start,end

def plate():
 pts,a,b=contour();N=len(pts)
 # The face is exactly planar. Only the deliberately ground edge tapers in Y.
 inner=list(pts)
 for i in range(a,b+1):
  width=W*math.sin(math.pi*(i-a)/(b-a))
  inner[i]=(pts[i][0]-width,pts[i][1])
 vertices=[]
 for side in [-1,1]:
  vertices.extend((x,CY+side*T,z) for x,z in inner)
  vertices.extend((x,CY+side*(.00030 if a<=i<=b else T),z) for i,(x,z) in enumerate(pts))
 faces=[tuple(range(N-1,-1,-1)),tuple(range(2*N,3*N))];mats=[0,0]
 for i in range(N):
  j=(i+1)%N
  if a-1<=i<=b:
   faces.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j)]);mats.extend([1,1])
  faces.append((N+i,N+j,3*N+j,3*N+i));mats.append(1 if a<=i<b else 0)
 mesh=bpy.data.meshes.new('HeadBody');mesh.from_pydata(vertices,[],faces);mesh.update()
 obj=bpy.data.objects.new('HeadBody',mesh);bpy.context.scene.collection.objects.link(obj)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 for f,mat in zip(mesh.polygons,mats):f.material_index=mat
 return obj,pts,a,b

def neck():
 obj=bpy.data.objects.new('JointNeck',factory.data.copy());bpy.context.scene.collection.objects.link(obj)
 activate(obj)
 if obj.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
  plane_co=(0,0,.130),plane_no=(0,0,1),clear_outer=True)
 ringedges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.13)<1e-5 for v in e.verts)]
 ringverts=set(v for e in ringedges for v in e.verts)
 bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(2),verts=list(ringverts),edges=ringedges,use_dissolve_boundaries=True)
 ringedges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.13)<1e-5 for v in e.verts)]
 ringverts=set(v for e in ringedges for v in e.verts)
 assert ringedges and len(ringedges)==len(ringverts),'Non-simple actual neck interface'
 center=sum((v.co for v in ringverts),Vector())/len(ringverts)
 original={v: v.co.copy() for v in ringverts}
 # Rounded-rectangle loft retains the exact stock lower end and flows into the clean head.
 for z in [.140,.153,.167,.183]:
  result=bmesh.ops.extrude_edge_only(bm,edges=ringedges)
  newverts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
  newedges=[e for e in result['geom'] if isinstance(e,bmesh.types.BMEdge) and all(v in newverts for v in e.verts)]
  mapping={}
  for v in newverts:
   nearest=min(original,key=lambda k:(k.co-v.co).length_squared)
   p=original[nearest];angle=math.atan2((p.y-center.y)/.008,(p.x-center.x)/.016)
   mapping[v]=p
   c,s=math.cos(angle),math.sin(angle)
   x=.0065+.0160*math.copysign(abs(c)**.25,c)
   y=CY+(T-.0004)*math.copysign(abs(s)**.25,s)
   t=smooth(.13,.18,z);v.co=(p.x*(1-t)+x*t,p.y*(1-t)+y*t,z)
  original=mapping
  ringedges=newedges
 bmesh.ops.holes_fill(bm,edges=ringedges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 return obj

def boolean(obj,tool,operation):
 activate(obj);mod=obj.modifiers.new('ManufacturedCut','BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=tool
 bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)

def finish_mesh(obj):
 activate(obj);bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 mod=obj.modifiers.new('MachinedMicroBevel','BEVEL');mod.width=.00035;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True
 bpy.ops.object.modifier_apply(modifier=mod.name)
 # Flat faces stay flat. Smooth only the rolled perimeter/connector, split at creases.
 for f in obj.data.polygons:f.use_smooth=abs(f.normal.y)<.99999
 bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
 bmesh.ops.dissolve_degenerate(bm,dist=.00001,edges=list(bm.edges))
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(32)
 bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bmesh.ops.dissolve_degenerate(bm,dist=.000002,edges=list(bm.edges))
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 groups={}
 for f in bm.faces:groups.setdefault(frozenset(f.verts),[]).append(f)
 internal=[f for group in groups.values() if len(group)==2 and group[0].normal.dot(group[1].normal)<-.99 for f in group]
 if internal:bmesh.ops.delete(bm,geom=internal,context='FACES_ONLY')
 loose=[e for e in bm.edges if not e.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
 bm.to_mesh(obj.data);bm.free()
 mod=obj.modifiers.new('AreaWeightedManufacturedNormals','WEIGHTED_NORMAL')
 mod.keep_sharp=True;mod.mode='FACE_AREA';mod.weight=50
 bpy.ops.object.modifier_apply(modifier=mod.name)
 return obj

def author_material(edge=False):
 mat,nt,bs,out=make_mat('Author_'+KIND+('_Edge' if edge else '_Face'))
 coord=node(nt,'ShaderNodeTexCoord')
 noise=node(nt,'ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1800;noise.inputs['Detail'].default_value=2
 nt.links.new(coord.outputs['Object'],noise.inputs['Vector']);pattern=noise.outputs['Fac']
 if KIND=='FoldedArc' and not edge:
  wave=node(nt,'ShaderNodeTexWave',wave_type='BANDS',bands_direction='Z');wave.inputs['Scale'].default_value=480
  wave.inputs['Distortion'].default_value=3;wave.inputs['Detail Scale'].default_value=1.2
  nt.links.new(coord.outputs['Object'],wave.inputs['Vector']);pattern=wave.outputs['Fac']
 a,b=(.36,.46) if edge else ((.15,.168) if KIND=='FoldedArc' else (.065,.085))
 base=mix(nt,pattern,(a,a*1.025,a*1.05,1),(b,b*1.025,b*1.05,1))
 rough=op(nt,'ADD',op(nt,'MULTIPLY',noise.outputs['Fac'],.045),.25 if edge else .37)
 pack=node(nt,'ShaderNodeCombineColor');pack.inputs[0].default_value=1;put(nt,pack.inputs[1],rough);pack.inputs[2].default_value=.95
 bump=node(nt,'ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.000008
 nt.links.new(noise.outputs['Fac'],bump.inputs['Height'])
 put(nt,bs.inputs['Base Color'],base);put(nt,bs.inputs['Roughness'],rough);bs.inputs['Metallic'].default_value=.95;nt.links.new(bump.outputs[0],bs.inputs['Normal'])
 return mat,{'BaseColor':base,'ORM':pack.outputs[0]},bs,out

body,outline,edge_start,edge_end=plate()
materials=[author_material(False),author_material(True)]
for m,*_ in materials:body.data.materials.append(m)
joint=neck();joint.data.materials.clear();joint.data.materials.append(materials[0][0])
boolean(body,joint,'UNION')
if KIND=='SwiftCrescent':
 for z in [.277,.290]:
  for side in [-1,1]:
   tool=cube('ShallowMachinedFuller',(.082,CY+side*(T+.0001),z),(.064,.0014,.0024),materials[0][0],.00065)
   boolean(body,tool,'DIFFERENCE')
body=finish_mesh(body);body.name='SM_TacticalHatchet_Head_'+KIND+'_R2'
if not body.data.uv_layers:body.data.uv_layers.new(name='UVMap')
unwrap(body)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU' if any(d.use for d in prefs.devices) else 'CPU'
maps=bake(body,materials,'T_TacticalHatchet_Head_'+KIND+'_R2',P/'Textures',2048)
fbx=P/'Export'/(body.name+'.fbx');export(body,fbx)
bm=bmesh.new();bm.from_mesh(body.data)
metrics={'vertices':len(bm.verts),'triangles':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),
 'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces),
 'signed_volume_cm3':bm.calc_volume(signed=True)*1e6,'body_thickness_cm':T*200,
 'dimensions_cm':[float(d)*100 for d in body.dimensions]}
print('TOPOLOGY_EDGES '+str([(len(e.link_faces),[tuple(v.co) for v in e.verts]) for e in bm.edges if not e.is_manifold][:20]),flush=True)
print('BAD_FACES '+str([[(tuple(f.normal),[tuple(v.co) for v in f.verts]) for f in e.link_faces] for e in bm.edges if not e.is_manifold][:2]),flush=True)
bm.free()
assert metrics['boundary_edges']==0 and metrics['nonmanifold_edges']==0 and metrics['degenerate_faces']==0,metrics
assert metrics['signed_volume_cm3']>0,metrics
entry={'id':ID,'name':LABEL,'slot':'blade_1','kind':KIND,'object':body.name,'fbx':str(fbx),'textures':maps,
 'origin_cm':[0,0,0],'mesh':'/Game/Weapons/TacticalHatchet20261101/ModulesV1/'+body.name+'.'+body.name,
 'material_slot':body.data.materials[0].name,'metrics':metrics,'model_revision':'clean_rebuild_v2_20261103',
 'trace_base_cm':[outline[edge_end][0]*100,-CY*100,outline[edge_end][1]*100],
 'trace_tip_cm':[outline[edge_start][0]*100,-CY*100,outline[edge_start][1]*100]}
(P/(KIND+'.json')).write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/(KIND+'_Editable.blend')))
print('HEAD_REBUILT '+KIND+' '+json.dumps(metrics),flush=True)
