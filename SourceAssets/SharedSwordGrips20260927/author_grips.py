"""Fit two approved grips to each sword's original end rims and hand envelope.

Blender background production. Copies stock UVs, finish colors and split normals
at both mounting ends. The new continuous loft supplies its own unwrapped PBR.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
HOSTS=json.loads((P/'mount_inputs.json').read_text())
TAU=math.tau;N=96;ROWS=192
ENDS={'Rune':(-.010,-.143),'Frost':(-.020,-.157),'Highland':(-.012,-.165)}
bpy.context.preferences.filepaths.save_version=0
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def angle(p):return math.atan2(p.y,p.x)%TAU
def clip(poly,z,above):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=(a[0].z-z)*(1 if above else -1);db=(b[0].z-z)*(1 if above else -1)
  if da>=0:result.append(a)
  if (da>=0)!=(db>=0):
   t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
 return result
class Builder:
 def __init__(self):self.v=[];self.f=[];self.c=[];self.mi=[];self.lookup={}
 def vertex(self,p):
  key=tuple(round(x,7) for x in p)
  if key not in self.lookup:self.lookup[key]=len(self.v);self.v.append(tuple(p))
  return self.lookup[key]
 def polygon(self,points,mat):
  for i in range(1,len(points)-1):
   tri=[points[0],points[i],points[i+1]]
   if (tri[1][0]-tri[0][0]).cross(tri[2][0]-tri[0][0]).length<1e-12:continue
   ids=[self.vertex(x[0]) for x in tri]
   if len(set(ids))<3:continue
   self.f.append(ids);self.c.extend(tri);self.mi.append(mat)
def generated(p,a,t,normal=None):
 return (p,Vector((a/TAU,t*1.5)),Vector((.97,.905)),Vector((1,1,1,1)),normal if normal is not None else Vector((p.x,p.y,0)).normalized())
def bridge(b,upper,lower,mat,t0,t1):
 upper=sorted(upper,key=lambda q:angle(q[0]));lower=sorted(lower,key=lambda q:angle(q[0]))
 i=j=0;nu=len(upper);nl=len(lower)
 def at(r,k,t):
  q=r[k%len(r)];a=angle(q[0])+(TAU if k>=len(r) else 0)
  return generated(q[0],a,t,q[4])
 while i<nu or j<nl:
  ua=angle(upper[(i+1)%nu][0])+(TAU if i+1>=nu else 0) if i<nu else 1e9
  la=angle(lower[(j+1)%nl][0])+(TAU if j+1>=nl else 0) if j<nl else 1e9
  if ua<=la:pts=[at(upper,i,t0),at(lower,j,t1),at(upper,i+1,t0)];i+=1
  else:pts=[at(upper,i,t0),at(lower,j,t1),at(lower,j+1,t1)];j+=1
  a=sum(angle(q[0]) for q in pts)/3
  b.polygon(pts,mat(a,(t0+t1)*.5))
def pbr(key):
 m=bpy.data.materials.new('M_SharedGrip_'+key);m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Metallic'].default_value=.9 if key=='Steel' else 0
 for suffix,target in [('BaseColor','Base Color'),('Normal','Normal'),('Roughness','Roughness')]:
  tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/(key+'_'+suffix+'.png')),check_existing=True)
  tex.image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
  output=tex.outputs['Color']
  if suffix=='Normal':
   normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(output,normal.inputs['Color']);output=normal.outputs['Normal']
  m.node_tree.links.new(output,bs.inputs[target])
 return m
models=[]
for host,spec in HOSTS.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 with bpy.data.libraries.load(str(P.parent/spec['blend']),link=False) as (a,bb):bb.objects=[spec['object']]
 src=bb.objects[0];source=src.data.copy();source.calc_loop_triangles()
 stock=source.materials[0].copy();stock.name='M_SharedGrip_'+host+'Mount'
 bvh=BVHTree.FromPolygons([v.co for v in source.vertices],[list(p.vertices) for p in source.polygons])
 normals=[x.vector.copy() for x in source.corner_normals]
 uv0=source.uv_layers[0].data
 uv1=source.uv_layers[1].data if len(source.uv_layers)>1 else None
 color=source.color_attributes.get('GuardFinish')
 materials=[stock,pbr('Leather'),pbr('Steel'),pbr('Textile')]
 top,bottom=ENDS[host]
 def radial(z,a):
  hit=bvh.ray_cast(Vector((0,0,z)),Vector((math.cos(a),math.sin(a),0)),.1)[0]
  if hit is None:raise RuntimeError(f'Missing source mounting surface {host} {z} {a}')
  return hit
 for key in ['iron_spine_power_grip','lockweave_guard_grip']:
  out=P/host/key;out.mkdir(parents=True,exist_ok=True)
  b=Builder();rings=[{},{}]
  for tri in source.loop_triangles:
   poly=[]
   for li in tri.loops:
    poly.append((source.vertices[source.loops[li].vertex_index].co.copy(),uv0[li].uv.copy(),uv1[li].uv.copy() if uv1 else Vector((0,0)),Vector(color.data[li].color) if color else Vector((1,1,1,1)),normals[li].copy()))
   for idx,(z,above) in enumerate([(top,True),(bottom,False)]):
    cropped=clip(poly,z,above)
    for q in cropped:
     if abs(q[0].z-z)<1e-7:rings[idx][tuple(round(c,7) for c in q[0])]=tuple(c.copy() for c in q)
    b.polygon(cropped,0)
  def weave(a,t):
   a1=abs(math.sin(math.pi*(t*7+a/TAU*4)))
   a2=abs(math.sin(math.pi*(t*7-a/TAU*4)))
   return max(math.exp(-((a1/.48)**4)),math.exp(-((a2/.48)**4)))
  def metal(a,t):
   if .03<t<.065 or .935<t<.97:return True
   if key=='iron_spine_power_grip':
    return abs(t-1/3)<.009 or abs(t-2/3)<.009 or (.065<t<.935 and abs(math.sin(a))<.14)
   return False
  def mat(a,t):
   if metal(a,t):return 2
   return 3 if key=='lockweave_guard_grip' and weave(a,t)>.18 else 1
  grid=[list(rings[0].values())]
  for row in range(1,ROWS):
   t=row/ROWS;z=top+(bottom-top)*t
   fade=smooth(t/.10)*smooth((1-t)/.10)
   ring=[]
   for i in range(N):
    a=TAU*i/N
    # Match exact source rim through a smooth transition, then retain its grasp envelope.
    if host=='Frost':
     # The original sculpt has deep wrap grooves: preserve its outer hand envelope,
     # not the old decorative grooves beneath the entirely new wrap.
     rx=.0147*(1-.055*math.sin(math.pi*t)**2);ry=.0226*(1-.055*math.sin(math.pi*t)**2)
     r=1/math.sqrt((math.cos(a)/rx)**2+(math.sin(a)/ry)**2)
     p=Vector((r*math.cos(a),r*math.sin(a),z))
    else:p=radial(z,a)
    end=radial(top,a) if t<.5 else radial(bottom,a)
    r=math.hypot(p.x,p.y);end_r=math.hypot(end.x,end.y)
    r=end_r*(1-fade)+r*fade
    if key=='iron_spine_power_grip':
     # Rounded eight-sided leather core and almost flush steel spines.
     depth=.00040+.00020*(1+math.cos(8*a))*.5
     if metal(a,t):depth=.00010
    else:
     depth=.00080-.00058*weave(a,t)
     if abs(t-.5)<.008:depth=.00012
     if metal(a,t):depth=.00008
    r-=depth*fade
    p=Vector((r*math.cos(a),r*math.sin(a),z))
    ring.append(generated(p,a,t))
   grid.append(ring)
  grid.append(list(rings[1].values()))
  for row in range(ROWS):bridge(b,grid[row],grid[row+1],mat,row/ROWS,(row+1)/ROWS)
  name=f'SM_{host}Grip_{key}'
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(b.v,[],b.f);mesh.update()
  for m in materials:mesh.materials.append(m)
  uva=mesh.uv_layers.new(name='UVMap');uvb=mesh.uv_layers.new(name='StockBronzeUV')
  col=mesh.color_attributes.new(name='GuardFinish',type='FLOAT_COLOR',domain='CORNER')
  for fi,face in enumerate(mesh.polygons):
   face.material_index=b.mi[fi];face.use_smooth=True
   for li in face.loop_indices:
    q=b.c[li];uva.data[li].uv=q[1];uvb.data[li].uv=q[2];col.data[li].color=q[3]
  mesh.update();custom=[x.vector.copy() for x in mesh.corner_normals]
  for face in mesh.polygons:
   for li in face.loop_indices:
    z=mesh.vertices[mesh.loops[li].vertex_index].co.z
    if face.material_index==0 or abs(z-top)<1e-7 or abs(z-bottom)<1e-7:custom[li]=b.c[li][4]
  mesh.normals_split_custom_set(custom)
  obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
  obj.matrix_world=Matrix.Identity(4)
  bpy.context.view_layer.objects.active=obj;obj.select_set(True)
  bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
  bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'_Editable.blend')),compress=True)
  row={'host':host,'weapon':spec['weapon'],'id':key,'mesh':name,'folder':str(out),'catalog':spec['catalog'],
   'source':spec['blend'],'stock_mesh':spec['factory']['mesh'],'stock_material_slot':'M_SharedGrip_'+host+'Mount',
   'length_cm':(spec['bounds'][1][2]-spec['bounds'][0][2])*100,'cut_planes_m':[top,bottom],
   'location_cm':spec['factory']['location_cm'],'interface':spec['factory']['interface'],
   'pommel_offset_cm':[0,0,0],'triangles':len(mesh.polygons),'grasp':'stock mounting rims; stock hand positions; no animation override'}
  models.append(row);print('GRIP_AUTHORED '+name,flush=True)
  bpy.data.objects.remove(obj,do_unlink=True)
(P/'models.json').write_text(json.dumps(models,indent=2),encoding='utf-8')
